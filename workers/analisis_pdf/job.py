"""Generate PDF for pending Estándar/Experta analisis_requests and pin to Pinata."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from supabase import Client, create_client

from workers.analisis_pdf.pinata import pin_pdf_to_pinata
from workers.analisis_pdf.render import render_pdf_bytes


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
        # unexpected object — treat as empty unless it looks like a row
        if "id" in data:
            return [data]
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def list_pending(sb: Client, limit: int) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_requests_pending_pdf", {"p_limit": limit}).execute().data
    return _as_list(data)


def set_pdf_cid(sb: Client, request_id: str, pdf_cid: str) -> dict[str, Any]:
    data = (
        sb.rpc(
            "set_analisis_request_pdf_cid",
            {"p_id": request_id, "p_pdf_cid": pdf_cid},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    return data


def process_row(sb: Client, row: dict[str, Any]) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    wallet = str(row.get("wallet") or "")
    analisis = row.get("analisis")
    if isinstance(analisis, str):
        analisis = json.loads(analisis)
    if not isinstance(analisis, dict):
        return {"id": request_id, "status": "skipped", "reason": "missing_analisis"}

    pdf_bytes = render_pdf_bytes(
        request_id=request_id,
        tier=tier,
        wallet=wallet,
        analisis=analisis,
        data_hash=row.get("data_hash"),
        analisis_cid=row.get("analisis_cid"),
    )
    cid = pin_pdf_to_pinata(pdf_bytes, request_id=request_id)
    result = set_pdf_cid(sb, request_id, cid)
    if not result.get("ok"):
        return {
            "id": request_id,
            "status": "rpc_failed",
            "pdf_cid": cid,
            "error": result.get("error"),
        }
    return {"id": request_id, "status": "ok", "pdf_cid": cid, "bytes": len(pdf_bytes)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walpulse analisis_pdf worker")
    parser.add_argument("--limit", type=int, default=20, help="Max rows per run (1-100)")
    parser.add_argument(
        "--dry-render",
        action="store_true",
        help="Render PDF only (no Pinata / no DB write); needs SUPABASE_* to list",
    )
    args = parser.parse_args(argv)
    limit = max(1, min(int(args.limit), 100))

    sb = supabase_client()
    pending = list_pending(sb, limit)
    print(json.dumps({"pending": len(pending), "limit": limit}), flush=True)

    if not pending:
        print(json.dumps({"status": "idle"}), flush=True)
        return 0

    results: list[dict[str, Any]] = []
    for row in pending:
        request_id = str(row.get("id"))
        try:
            if args.dry_render:
                analisis = row.get("analisis")
                if isinstance(analisis, str):
                    analisis = json.loads(analisis)
                pdf_bytes = render_pdf_bytes(
                    request_id=request_id,
                    tier=str(row.get("tier") or ""),
                    wallet=str(row.get("wallet") or ""),
                    analisis=analisis if isinstance(analisis, dict) else {},
                    data_hash=row.get("data_hash"),
                    analisis_cid=row.get("analisis_cid"),
                )
                results.append(
                    {"id": request_id, "status": "dry_render", "bytes": len(pdf_bytes)}
                )
            else:
                results.append(process_row(sb, row))
        except Exception as e:  # noqa: BLE001 — continue batch
            print(f"error id={request_id}: {e}", file=sys.stderr, flush=True)
            results.append({"id": request_id, "status": "error", "error": str(e)[:500]})

    ok = sum(1 for r in results if r.get("status") == "ok")
    print(json.dumps({"processed": len(results), "ok": ok, "results": results}), flush=True)
    return 0 if ok == len(results) or (ok > 0 and all(r.get("status") != "error" for r in results)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
