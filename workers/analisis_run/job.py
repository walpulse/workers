"""GHA worker: claim FIFO + orchestrate Estándar/Experta analysis via Edge children."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from supabase import Client, create_client

from workers.analisis_run.pipelines import call_entregables, run_pipeline

STALE_MINUTES = 12
PARENT_TIMEOUT_S = {
    "estandar": 45 * 60,
    "experta": 90 * 60,
}


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


def claim_pending(sb: Client, limit: int = 1, stale_mins: int = STALE_MINUTES) -> list[dict[str, Any]]:
    data = (
        sb.rpc(
            "claim_analisis_requests_for_run",
            {"p_limit": limit, "p_stale_running_minutes": stale_mins},
        )
        .execute()
        .data
    )
    return _as_list(data)


def get_request(sb: Client, request_id: str) -> dict[str, Any] | None:
    data = sb.rpc("get_analisis_request", {"p_id": request_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


def update_request(sb: Client, request_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    data = (
        sb.rpc(
            "update_analisis_request",
            {"p_id": request_id, "p_patch": patch},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    return data if isinstance(data, dict) else {}


def mark_failed(sb: Client, request_id: str, message: str) -> None:
    update_request(
        sb,
        request_id,
        {"status": "failed", "error_message": message[:1000]},
    )


def process_row(sb: Client, row: dict[str, Any]) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    wallet = str(row.get("wallet") or "").lower()
    if tier not in {"estandar", "experta"}:
        return {"id": request_id, "status": "skipped", "reason": "tier_not_eligible"}
    if not wallet:
        mark_failed(sb, request_id, "missing_wallet")
        return {"id": request_id, "status": "failed", "reason": "missing_wallet"}

    # Ensure status running (claim already set it; force for --request-id path)
    update_request(sb, request_id, {"status": "running"})

    started = time.monotonic()
    deadline = started + PARENT_TIMEOUT_S.get(tier, 45 * 60)
    try:
        pipeline = run_pipeline(tier, wallet, request_id)
        if time.monotonic() > deadline:
            raise TimeoutError(f"parent_timeout_{tier}")

        final_status = "succeeded" if pipeline["compliance_ok"] else "succeeded_with_warnings"
        update_request(
            sb,
            request_id,
            {
                "analisis": pipeline["analisis"],
                "evidencia": pipeline["evidencia"],
                "upstream_errors": pipeline["upstream_errors"],
                "compliance_screen": pipeline["compliance_column"],
                "analyzed_at": pipeline["generated_at"],
            },
        )

        pack = call_entregables(request_id, final_status)
        if not pack.ok:
            err = str(pack.body.get("error") or f"packaging_http_{pack.status}")
            update_request(
                sb,
                request_id,
                {"status": "packaging_failed", "error_message": err[:1000]},
            )
            return {
                "id": request_id,
                "status": "packaging_failed",
                "error": err,
                "elapsed_s": round(time.monotonic() - started, 1),
            }

        return {
            "id": request_id,
            "status": final_status,
            "tier": tier,
            "wallet": wallet,
            "elapsed_s": round(time.monotonic() - started, 1),
            "pack": {k: pack.body.get(k) for k in ("analisis_cid", "evidencia_cid", "status") if k in pack.body},
        }
    except Exception as e:  # noqa: BLE001 — never leave silent running zombie
        msg = str(e)[:1000]
        print(f"analisis_run_failed id={request_id} err={msg}", file=sys.stderr)
        mark_failed(sb, request_id, msg)
        return {
            "id": request_id,
            "status": "failed",
            "error": msg,
            "elapsed_s": round(time.monotonic() - started, 1),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orchestrate Estándar/Experta analisis runs")
    parser.add_argument("--limit", type=int, default=1, help="Max claims this oneshot (1–10)")
    parser.add_argument(
        "--request-id",
        action="append",
        default=[],
        help="Process specific request UUID (skips claim; may repeat)",
    )
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=STALE_MINUTES,
        help="Stale reclaim minutes for claim RPC",
    )
    args = parser.parse_args(argv)

    limit = max(1, min(int(args.limit or 1), 10))
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
        rows = claim_pending(sb, limit=limit, stale_mins=args.stale_minutes)

    if not rows:
        print(json.dumps({"status": "idle"}))
        return 0

    results = []
    for row in rows:
        results.append(process_row(sb, row))

    print(json.dumps({"status": "ok", "processed": len(results), "results": results}, default=str))
    # Non-zero only if all failed hard (ops signal); partial OK stays 0
    if results and all(r.get("status") == "failed" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
