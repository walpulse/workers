"""Send transactional email when analisis PDF (pdf_cid) is ready."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from workers.analisis_email.resend_client import send_email
from workers.analisis_email.templates import build_email


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
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def list_pending(sb: Client, limit: int) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_requests_pending_email", {"p_limit": limit}).execute().data
    return _as_list(data)


def get_request(sb: Client, request_id: str) -> dict[str, Any] | None:
    data = sb.rpc("get_analisis_request", {"p_id": request_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict) or not data.get("id"):
        return None
    return data


def _email_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def resolve_notify_email(sb: Client, row: dict[str, Any]) -> str | None:
    """Prefer request.email, then list RPC notify_email, else clientes.email."""
    # Per-request override (accept API / get_analisis_request).
    for key in ("email", "notify_email"):
        found = _email_or_none(row.get(key))
        if found:
            return found
    cliente_id = row.get("cliente_id")
    if not cliente_id:
        return None
    data = sb.rpc("get_cliente_email", {"p_cliente_id": str(cliente_id)}).execute().data
    return _email_or_none(data)


def set_email_sent(sb: Client, request_id: str, message_id: str) -> dict[str, Any]:
    data = (
        sb.rpc(
            "set_analisis_request_email_sent",
            {"p_id": request_id, "p_message_id": message_id},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    return data


def overwrite_email_sent(sb: Client, request_id: str, message_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    data = (
        sb.rpc(
            "update_analisis_request",
            {
                "p_id": request_id,
                "p_patch": {
                    "email_sent_at": now,
                    "email_message_id": message_id,
                },
            },
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    if (data.get("email_message_id") or "") != message_id:
        return {"ok": False, "error": "email_message_id_not_updated", "row": data}
    return {"ok": True, "row": data}


def process_row(sb: Client, row: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    if tier not in {"estandar", "experta"}:
        return {"id": request_id, "status": "skipped", "reason": "tier_not_eligible"}
    if not row.get("pdf_cid"):
        return {"id": request_id, "status": "skipped", "reason": "missing_pdf_cid"}
    if row.get("email_sent_at") and not force:
        return {"id": request_id, "status": "skipped", "reason": "already_sent"}

    to = resolve_notify_email(sb, row)
    if not to:
        return {"id": request_id, "status": "skipped", "reason": "missing_notify_email"}

    content = build_email(row)
    sent = send_email(
        to=to,
        subject=content["subject"],
        html=content["html"],
        text=content["text"],
    )
    message_id = str(sent["id"])
    result = (
        overwrite_email_sent(sb, request_id, message_id)
        if force
        else set_email_sent(sb, request_id, message_id)
    )
    if not result.get("ok"):
        return {
            "id": request_id,
            "status": "rpc_failed",
            "message_id": message_id,
            "to": to,
            "error": result.get("error"),
        }
    return {
        "id": request_id,
        "status": "ok",
        "to": to,
        "message_id": message_id,
        "pdf_url": content.get("pdf_url"),
        "forced": force,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walpulse analisis_email worker")
    parser.add_argument("--limit", type=int, default=20, help="Max rows per run (1-100)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Resend and overwrite email_sent_at / email_message_id",
    )
    parser.add_argument(
        "--request-id",
        action="append",
        default=[],
        help="Process specific request UUID (repeatable)",
    )
    args = parser.parse_args(argv)
    limit = max(1, min(int(args.limit), 100))

    sb = supabase_client()
    if args.request_id:
        rows: list[dict[str, Any]] = []
        for rid in args.request_id:
            row = get_request(sb, rid)
            if row is None:
                print(json.dumps({"id": rid, "status": "not_found"}), flush=True)
            else:
                rows.append(row)
        rows = rows[:limit]
    else:
        rows = list_pending(sb, limit)

    print(
        json.dumps(
            {
                "pending": len(rows),
                "limit": limit,
                "force": bool(args.force),
                "request_ids": args.request_id or None,
            }
        ),
        flush=True,
    )

    if not rows:
        print(json.dumps({"status": "idle"}), flush=True)
        return 0

    results: list[dict[str, Any]] = []
    for row in rows:
        request_id = str(row.get("id"))
        try:
            results.append(process_row(sb, row, force=bool(args.force)))
        except Exception as e:  # noqa: BLE001 — continue batch
            print(f"error id={request_id}: {e}", file=sys.stderr, flush=True)
            results.append({"id": request_id, "status": "error", "error": str(e)[:500]})

    ok = sum(1 for r in results if r.get("status") == "ok")
    print(json.dumps({"processed": len(results), "ok": ok, "results": results}), flush=True)
    hard_fail = any(r.get("status") == "error" for r in results)
    return 0 if (ok == len(results) or (ok > 0 and not hard_fail)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
