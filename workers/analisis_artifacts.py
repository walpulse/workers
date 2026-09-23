"""Storage-only helpers for analisis JSON artifacts (ADR 2026-09-23).

Bucket: analisis-artifacts
Path: {cliente_id}/{request_id}/{kind}.json
Catalog: upsert_analisis_artifact / list_analisis_artifacts
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

ARTIFACT_BUCKET = "analisis-artifacts"

ArtifactKind = str  # request_payload | analisis | evidencia | ... | riesgo

KNOWN_KINDS = frozenset({
    "request_payload",
    "analisis",
    "evidencia",
    "manifiesto",
    "signature",
    "onchain",
    "compliance_screen",
    "upstream_errors",
    "run_progress",
    "riesgo",
    "receipt",
})


def artifact_path(cliente_id: str, request_id: str, kind: str) -> str:
    return f"{cliente_id}/{request_id}/{kind}.json"


def put_analisis_artifact(
    sb: Client,
    cliente_id: str,
    request_id: str,
    kind: str,
    body: Any,
) -> dict[str, Any]:
    """Upload JSON to Storage + upsert catalog. Raises on upload failure."""
    if body is None:
        raise ValueError(f"artifact_body_required:{kind}")
    kind_norm = str(kind or "").strip().lower()
    if kind_norm not in KNOWN_KINDS:
        raise ValueError(f"invalid_artifact_kind:{kind}")

    path = artifact_path(str(cliente_id), str(request_id), kind_norm)
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sha256 = hashlib.sha256(raw).hexdigest()

    up = sb.storage.from_(ARTIFACT_BUCKET).upload(
        path,
        raw,
        file_options={
            "content-type": "application/json",
            "upsert": "true",
        },
    )
    # supabase-py may return dict with error or raise
    if isinstance(up, dict) and up.get("error"):
        raise RuntimeError(f"artifact_upload_failed:{kind_norm}:{up['error']}")

    cat = (
        sb.rpc(
            "upsert_analisis_artifact",
            {
                "p_request_id": request_id,
                "p_kind": kind_norm,
                "p_storage_path": path,
                "p_sha256": sha256,
                "p_byte_size": len(raw),
            },
        )
        .execute()
        .data
    )
    if cat is None:
        logger.warning("analisis_artifact_catalog_empty kind=%s request_id=%s", kind_norm, request_id)

    return {"path": path, "sha256": sha256, "byte_size": len(raw), "kind": kind_norm}


def put_analisis_artifacts(
    sb: Client,
    cliente_id: str,
    request_id: str,
    artifacts: dict[str, Any],
) -> list[dict[str, Any]]:
    """Upload multiple kinds. Skips keys whose body is None."""
    out: list[dict[str, Any]] = []
    for kind, body in artifacts.items():
        if body is None:
            continue
        out.append(put_analisis_artifact(sb, cliente_id, request_id, kind, body))
    return out


def list_artifacts(sb: Client, request_id: str) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_artifacts", {"p_request_id": request_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def download_artifact(sb: Client, path: str) -> Any | None:
    try:
        raw = sb.storage.from_(ARTIFACT_BUCKET).download(path)
    except Exception as e:  # noqa: BLE001
        logger.error("analisis_artifact_download_failed path=%s err=%s", path, e)
        return None
    if raw is None:
        return None
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    else:
        text = str(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("analisis_artifact_invalid_json path=%s", path)
        return None


def require_artifact(sb: Client, request_id: str, kind: str) -> Any | None:
    """Load artifact from Storage via catalog. No jsonb column fallback."""
    kind_norm = str(kind or "").strip().lower()
    rows = list_artifacts(sb, request_id)
    path = None
    for row in rows:
        if str(row.get("kind") or "").lower() == kind_norm:
            path = row.get("storage_path")
            break
    if not path:
        return None
    return download_artifact(sb, str(path))


def control_plane_from_analisis(
    analisis: dict[str, Any],
    *,
    compliance_column: dict[str, Any] | None = None,
    idioma: str = "es",
) -> dict[str, Any]:
    """Derive typed control-plane fields from analisis-v1 (for update patch)."""
    syn = analisis.get("synthesis") if isinstance(analisis.get("synthesis"), dict) else {}
    mods = analisis.get("modules") if isinstance(analisis.get("modules"), dict) else {}
    lang_key = {"en": "eng", "pt": "por"}.get(idioma or "es", "esp")

    def _grade(mod: Any) -> str | None:
        if not isinstance(mod, dict):
            return None
        g = mod.get("grade")
        if isinstance(g, str) and g in {"A", "B", "C", "D", "F"}:
            return g
        return None

    grade = _grade(syn) if syn else None
    if grade is None:
        g = syn.get("grade") if syn else None
        if isinstance(g, str) and g in {"A", "B", "C", "D", "F"}:
            grade = g

    label = None
    gl = syn.get("grade_label") if syn else None
    if isinstance(gl, dict):
        label = (
            gl.get(lang_key)
            or gl.get("esp")
            or gl.get("eng")
            or gl.get("por")
            or None
        )
        if label is not None:
            label = str(label).strip() or None
    elif isinstance(gl, str):
        label = gl.strip() or None

    custody = None
    cc = analisis.get("custody_classification")
    if isinstance(cc, dict):
        raw = cc.get("class")
        if isinstance(raw, str) and raw in {
            "hosted_known",
            "hosted_deposit_inferred",
            "likely_unhosted",
            "unknown",
        }:
            custody = raw

    patch: dict[str, Any] = {
        "has_analisis_artifact": True,
        "grade": grade,
        "grade_label": label,
        "grade_origins": _grade(mods.get("origins")),
        "grade_activity": _grade(mods.get("activity")),
        "grade_multichain": _grade(mods.get("multichain")),
        "grade_portfolio": _grade(mods.get("portfolio")),
        "custody_class": custody,
    }

    if isinstance(compliance_column, dict):
        status = compliance_column.get("status")
        if status is not None:
            patch["compliance_status"] = str(status)
        if "sanctioned" in compliance_column:
            patch["compliance_sanctioned"] = bool(compliance_column.get("sanctioned"))
        if "any_list_match" in compliance_column:
            patch["compliance_any_list_match"] = bool(compliance_column.get("any_list_match"))

    return patch


def riesgo_tiene_evaluaciones(riesgo: dict[str, Any] | None) -> bool:
    if not isinstance(riesgo, dict):
        return False
    ev = riesgo.get("evaluations")
    return isinstance(ev, list) and len(ev) > 0
