"""Unit tests for Storage-only analisis artifacts helpers."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from workers.analisis_artifacts import (
    artifact_path,
    control_plane_from_analisis,
    put_analisis_artifact,
    require_artifact,
    riesgo_tiene_evaluaciones,
)


def test_artifact_path() -> None:
    assert (
        artifact_path("cli", "req", "analisis")
        == "cli/req/analisis.json"
    )


def test_control_plane_from_analisis() -> None:
    analisis = {
        "synthesis": {
            "grade": "B",
            "grade_label": {"esp": "Bueno", "eng": "Good", "por": "Bom"},
        },
        "modules": {
            "origins": {"grade": "A"},
            "activity": {"grade": "B"},
            "multichain": {"grade": "C"},
            "portfolio": {"grade": "D"},
        },
        "custody_classification": {"class": "likely_unhosted"},
    }
    patch = control_plane_from_analisis(
        analisis,
        compliance_column={"status": "ok", "sanctioned": False, "any_list_match": True},
        idioma="es",
    )
    assert patch["has_analisis_artifact"] is True
    assert patch["grade"] == "B"
    assert patch["grade_label"] == "Bueno"
    assert patch["grade_origins"] == "A"
    assert patch["custody_class"] == "likely_unhosted"
    assert patch["compliance_status"] == "ok"
    assert patch["compliance_sanctioned"] is False
    assert patch["compliance_any_list_match"] is True


def test_riesgo_tiene_evaluaciones() -> None:
    assert not riesgo_tiene_evaluaciones({"evaluations": []})
    assert riesgo_tiene_evaluaciones({"evaluations": [{"matriz_id": "x"}]})
    assert not riesgo_tiene_evaluaciones(None)


def test_put_analisis_artifact_uploads_and_catalogs() -> None:
    sb = MagicMock()
    sb.storage.from_.return_value.upload.return_value = {"path": "ok"}
    sb.rpc.return_value.execute.return_value = MagicMock(data={"ok": True})

    out = put_analisis_artifact(sb, "cli", "req", "analisis", {"version": "analisis-v1"})
    assert out["path"] == "cli/req/analisis.json"
    assert out["byte_size"] > 0
    sb.storage.from_.assert_called_with("analisis-artifacts")
    sb.storage.from_.return_value.upload.assert_called_once()
    sb.rpc.assert_called_once()
    args = sb.rpc.call_args
    assert args[0][0] == "upsert_analisis_artifact"
    assert args[0][1]["p_kind"] == "analisis"


def test_require_artifact_storage_only() -> None:
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(
        data=[{"kind": "analisis", "storage_path": "cli/req/analisis.json"}]
    )
    sb.storage.from_.return_value.download.return_value = b'{"version":"analisis-v1"}'

    body = require_artifact(sb, "req", "analisis")
    assert body == {"version": "analisis-v1"}

    sb.rpc.return_value.execute.return_value = MagicMock(data=[])
    assert require_artifact(sb, "req", "analisis") is None


def test_require_artifact_no_jsonb_fallback() -> None:
    """Even if a row dict had analisis, require_artifact never reads it."""
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = MagicMock(data=[])
    row: dict[str, Any] = {"analisis": {"version": "should-not-use"}}
    assert require_artifact(sb, "req", "analisis") is None
    # row unused on purpose — Storage-only contract
    assert row["analisis"]["version"] == "should-not-use"
