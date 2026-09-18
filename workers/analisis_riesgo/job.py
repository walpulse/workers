"""Evaluate pending Estándar/Experta requests against client risk matrices."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from supabase import Client, create_client

from workers.analisis_riesgo.evaluate import evaluate_request, skip_envelope


def _env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def supabase_client() -> Client:
    return create_client(_env("SUPABASE_URL"), _env("SUPABASE_SERVICE_ROLE_KEY"))


def _as_list(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict):
        if "id" in data:
            return [data]
        if "matrices" in data:
            return []
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def list_pending(sb: Client, limit: int) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_requests_pending_riesgo", {"p_limit": limit}).execute().data
    return _as_list(data)


def get_request(sb: Client, request_id: str) -> dict[str, Any] | None:
    data = sb.rpc("get_analisis_request", {"p_id": request_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def get_matrices(sb: Client, cliente_id: str) -> dict[str, Any]:
    data = sb.rpc("get_cliente_riesgo_matrices_activas", {"p_cliente_id": cliente_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    return data if isinstance(data, dict) else {"tiene_matrices_activas": False, "matrices": []}


def set_riesgo(sb: Client, request_id: str, riesgo: dict[str, Any]) -> dict[str, Any]:
    data = (
        sb.rpc(
            "set_analisis_request_riesgo",
            {"p_id": request_id, "p_riesgo": riesgo},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    return data


def overwrite_riesgo(sb: Client, request_id: str, riesgo: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    data = (
        sb.rpc(
            "update_analisis_request",
            {
                "p_id": request_id,
                "p_patch": {"riesgo": riesgo, "riesgo_evaluado_at": now},
            },
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    return {"ok": True, "row": data}


def process_row(sb: Client, row: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    if tier not in {"estandar", "experta"}:
        return {"id": request_id, "status": "skipped", "reason": "tier_not_eligible"}

    if row.get("riesgo_evaluado_at") and not force:
        return {"id": request_id, "status": "skipped", "reason": "already_evaluated"}

    analisis = row.get("analisis")
    if isinstance(analisis, str):
        analisis = json.loads(analisis)
    if not isinstance(analisis, dict):
        return {"id": request_id, "status": "skipped", "reason": "missing_analisis"}

    cliente_id = row.get("cliente_id")
    if not cliente_id:
        # Defense: mark skip so PDF is not blocked
        payload = skip_envelope(request_id)
        result = overwrite_riesgo(sb, request_id, payload) if force else set_riesgo(sb, request_id, payload)
        return {
            "id": request_id,
            "status": "ok" if result.get("ok") else "error",
            "skipped_reason": "missing_cliente_id",
            "rpc": result,
        }

    ctx = get_matrices(sb, str(cliente_id))
    matrices = ctx.get("matrices") if isinstance(ctx.get("matrices"), list) else []
    payload = evaluate_request(analisis, matrices, request_id=request_id)

    if force:
        result = overwrite_riesgo(sb, request_id, payload)
    else:
        result = set_riesgo(sb, request_id, payload)

    return {
        "id": request_id,
        "status": "ok" if result.get("ok") else "error",
        "skipped_reason": payload.get("skipped_reason"),
        "evaluations": len(payload.get("evaluations") or []),
        "rpc": result if not result.get("ok") else {"ok": True},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Motor de Riesgos for pending analisis")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--request-id", action="append", default=[])
    parser.add_argument("--force", action="store_true", help="Overwrite riesgo_evaluado_at")
    args = parser.parse_args(argv)

    limit = max(1, min(int(args.limit or 20), 100))
    sb = supabase_client()

    rows: list[dict[str, Any]] = []
    if args.request_id:
        for rid in args.request_id:
            rid = (rid or "").strip()
            if not rid:
                continue
            row = get_request(sb, rid)
            if not row:
                print(json.dumps({"id": rid, "status": "skipped", "reason": "not_found"}))
                continue
            rows.append(row)
    else:
        rows = list_pending(sb, limit)

    if not rows:
        print(json.dumps({"status": "idle"}))
        return 0

    results = [process_row(sb, row, force=bool(args.force)) for row in rows]
    print(json.dumps({"status": "ok", "processed": len(results), "results": results}, default=str))
    if results and all(r.get("status") == "error" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
