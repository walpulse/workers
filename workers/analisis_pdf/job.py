"""Generate PDF for pending Estándar/Experta analisis_requests and pin to Pinata.

Also generates a Motor de Riesgos PDF (riesgo_cid) when evaluations are present.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from supabase import Client, create_client

from workers.analisis_pdf.pinata import pin_pdf_to_pinata
from workers.analisis_pdf.render import render_pdf_bytes
from workers.analisis_pdf.render_riesgo import has_riesgo_evaluations, render_riesgo_pdf_bytes


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


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def list_pending(sb: Client, limit: int) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_requests_pending_pdf", {"p_limit": limit}).execute().data
    return _as_list(data)


def list_pending_riesgo_pdf(sb: Client, limit: int) -> list[dict[str, Any]]:
    data = sb.rpc("list_analisis_requests_pending_riesgo_pdf", {"p_limit": limit}).execute().data
    return _as_list(data)


def get_request(sb: Client, request_id: str) -> dict[str, Any] | None:
    data = sb.rpc("get_analisis_request", {"p_id": request_id}).execute().data
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict) and data.get("id"):
        return data
    return None


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


def overwrite_pdf_cid(sb: Client, request_id: str, pdf_cid: str) -> dict[str, Any]:
    data = (
        sb.rpc(
            "update_analisis_request",
            {"p_id": request_id, "p_patch": {"pdf_cid": pdf_cid}},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    if (data.get("pdf_cid") or "") != pdf_cid:
        return {"ok": False, "error": "pdf_cid_not_updated", "row": data}
    return {"ok": True, "row": data}


def set_riesgo_cid(sb: Client, request_id: str, riesgo_cid: str) -> dict[str, Any]:
    data = (
        sb.rpc(
            "set_analisis_request_riesgo_cid",
            {"p_id": request_id, "p_riesgo_cid": riesgo_cid},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    return data


def overwrite_riesgo_cid(sb: Client, request_id: str, riesgo_cid: str) -> dict[str, Any]:
    data = (
        sb.rpc(
            "update_analisis_request",
            {"p_id": request_id, "p_patch": {"riesgo_cid": riesgo_cid}},
        )
        .execute()
        .data
    )
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        return {"ok": False, "error": "unexpected_rpc_response"}
    if (data.get("riesgo_cid") or "") != riesgo_cid:
        return {"ok": False, "error": "riesgo_cid_not_updated", "row": data}
    return {"ok": True, "row": data}


def process_row(sb: Client, row: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    wallet = str(row.get("wallet") or "")
    analisis = _parse_json_field(row.get("analisis"))
    if not isinstance(analisis, dict):
        return {"id": request_id, "status": "skipped", "reason": "missing_analisis"}

    if tier not in {"estandar", "experta"}:
        return {"id": request_id, "status": "skipped", "reason": "tier_not_eligible"}
    if not row.get("analisis_cid"):
        return {"id": request_id, "status": "skipped", "reason": "missing_analisis_cid"}

    pdf_bytes = render_pdf_bytes(
        request_id=request_id,
        tier=tier,
        wallet=wallet,
        analisis=analisis,
        data_hash=row.get("data_hash"),
        analisis_cid=row.get("analisis_cid"),
        evidencia_cid=row.get("evidencia_cid"),
        idioma=row.get("idioma"),
    )
    cid = pin_pdf_to_pinata(pdf_bytes, request_id=request_id, filename_prefix="analisis")
    result = overwrite_pdf_cid(sb, request_id, cid) if force else set_pdf_cid(sb, request_id, cid)
    if not result.get("ok"):
        return {
            "id": request_id,
            "status": "rpc_failed",
            "kind": "analisis",
            "pdf_cid": cid,
            "error": result.get("error"),
        }
    return {
        "id": request_id,
        "status": "ok",
        "kind": "analisis",
        "pdf_cid": cid,
        "bytes": len(pdf_bytes),
        "forced": force,
    }


def process_riesgo_row(
    sb: Client, row: dict[str, Any], *, force: bool = False
) -> dict[str, Any]:
    request_id = str(row["id"])
    tier = str(row.get("tier") or "")
    wallet = str(row.get("wallet") or "")
    riesgo = _parse_json_field(row.get("riesgo"))

    if tier not in {"estandar", "experta"}:
        return {
            "id": request_id,
            "status": "skipped",
            "kind": "riesgo",
            "reason": "tier_not_eligible",
        }
    if not has_riesgo_evaluations(riesgo):
        return {
            "id": request_id,
            "status": "skipped",
            "kind": "riesgo",
            "reason": "no_evaluations",
        }
    assert isinstance(riesgo, dict)

    pdf_bytes = render_riesgo_pdf_bytes(
        request_id=request_id,
        tier=tier,
        wallet=wallet,
        riesgo=riesgo,
        idioma=row.get("idioma"),
    )
    cid = pin_pdf_to_pinata(
        pdf_bytes, request_id=request_id, filename_prefix="analisis-riesgo"
    )
    result = (
        overwrite_riesgo_cid(sb, request_id, cid)
        if force
        else set_riesgo_cid(sb, request_id, cid)
    )
    if not result.get("ok"):
        return {
            "id": request_id,
            "status": "rpc_failed",
            "kind": "riesgo",
            "riesgo_cid": cid,
            "error": result.get("error"),
        }
    return {
        "id": request_id,
        "status": "ok",
        "kind": "riesgo",
        "riesgo_cid": cid,
        "bytes": len(pdf_bytes),
        "forced": force,
    }


def _dry_render_analisis(row: dict[str, Any]) -> dict[str, Any]:
    request_id = str(row.get("id"))
    analisis = _parse_json_field(row.get("analisis"))
    pdf_bytes = render_pdf_bytes(
        request_id=request_id,
        tier=str(row.get("tier") or ""),
        wallet=str(row.get("wallet") or ""),
        analisis=analisis if isinstance(analisis, dict) else {},
        data_hash=row.get("data_hash"),
        analisis_cid=row.get("analisis_cid"),
        evidencia_cid=row.get("evidencia_cid"),
        idioma=row.get("idioma"),
    )
    return {
        "id": request_id,
        "status": "dry_render",
        "kind": "analisis",
        "bytes": len(pdf_bytes),
    }


def _dry_render_riesgo(row: dict[str, Any]) -> dict[str, Any]:
    request_id = str(row.get("id"))
    riesgo = _parse_json_field(row.get("riesgo"))
    if not has_riesgo_evaluations(riesgo):
        return {
            "id": request_id,
            "status": "skipped",
            "kind": "riesgo",
            "reason": "no_evaluations",
        }
    assert isinstance(riesgo, dict)
    pdf_bytes = render_riesgo_pdf_bytes(
        request_id=request_id,
        tier=str(row.get("tier") or ""),
        wallet=str(row.get("wallet") or ""),
        riesgo=riesgo,
        idioma=row.get("idioma"),
    )
    return {
        "id": request_id,
        "status": "dry_render",
        "kind": "riesgo",
        "bytes": len(pdf_bytes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walpulse analisis_pdf worker")
    parser.add_argument("--limit", type=int, default=20, help="Max rows per queue (1-100)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite pdf_cid / riesgo_cid via update_analisis_request after re-pin",
    )
    parser.add_argument(
        "--request-id",
        action="append",
        default=[],
        help="Process specific request UUID (repeatable). With --force, regenerates CIDs.",
    )
    parser.add_argument(
        "--dry-render",
        action="store_true",
        help="Render PDF only (no Pinata / no DB write); needs SUPABASE_* to list",
    )
    parser.add_argument(
        "--analisis-only",
        action="store_true",
        help="Only process analysis PDFs (pdf_cid)",
    )
    parser.add_argument(
        "--riesgo-only",
        action="store_true",
        help="Only process Motor de Riesgos PDFs (riesgo_cid)",
    )
    args = parser.parse_args(argv)
    if args.analisis_only and args.riesgo_only:
        raise SystemExit("use only one of --analisis-only / --riesgo-only")
    limit = max(1, min(int(args.limit), 100))
    do_analisis = not args.riesgo_only
    do_riesgo = not args.analisis_only

    sb = supabase_client()
    analisis_rows: list[dict[str, Any]] = []
    riesgo_rows: list[dict[str, Any]] = []

    if args.request_id:
        for rid in args.request_id:
            row = get_request(sb, rid)
            if row is None:
                print(json.dumps({"id": rid, "status": "not_found"}), flush=True)
                continue
            if do_analisis:
                analisis_rows.append(row)
            if do_riesgo:
                riesgo_rows.append(row)
        analisis_rows = analisis_rows[:limit]
        riesgo_rows = riesgo_rows[:limit]
    else:
        if do_analisis:
            analisis_rows = list_pending(sb, limit)
        if do_riesgo:
            riesgo_rows = list_pending_riesgo_pdf(sb, limit)

    print(
        json.dumps(
            {
                "pending_analisis": len(analisis_rows),
                "pending_riesgo": len(riesgo_rows),
                "limit": limit,
                "force": bool(args.force),
                "analisis_only": bool(args.analisis_only),
                "riesgo_only": bool(args.riesgo_only),
                "request_ids": args.request_id or None,
            }
        ),
        flush=True,
    )

    if not analisis_rows and not riesgo_rows:
        print(json.dumps({"status": "idle"}), flush=True)
        return 0

    results: list[dict[str, Any]] = []

    def _run(kind: str, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            request_id = str(row.get("id"))
            try:
                if args.dry_render:
                    if kind == "analisis":
                        results.append(_dry_render_analisis(row))
                    else:
                        results.append(_dry_render_riesgo(row))
                elif kind == "analisis":
                    results.append(process_row(sb, row, force=bool(args.force)))
                else:
                    results.append(process_riesgo_row(sb, row, force=bool(args.force)))
            except Exception as e:  # noqa: BLE001 — continue batch
                print(f"error kind={kind} id={request_id}: {e}", file=sys.stderr, flush=True)
                results.append(
                    {
                        "id": request_id,
                        "status": "error",
                        "kind": kind,
                        "error": str(e)[:500],
                    }
                )

    if do_analisis:
        _run("analisis", analisis_rows)
    if do_riesgo:
        _run("riesgo", riesgo_rows)

    ok = sum(1 for r in results if r.get("status") == "ok")
    dry = sum(1 for r in results if r.get("status") == "dry_render")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    errors = sum(1 for r in results if r.get("status") == "error")
    print(
        json.dumps(
            {
                "processed": len(results),
                "ok": ok,
                "dry_render": dry,
                "skipped": skipped,
                "errors": errors,
                "results": results,
            }
        ),
        flush=True,
    )
    if errors:
        return 1
    if args.dry_render:
        return 0
    actionable = [r for r in results if r.get("status") not in {"skipped"}]
    if not actionable:
        return 0
    return 0 if ok == len(actionable) else 1


if __name__ == "__main__":
    raise SystemExit(main())
