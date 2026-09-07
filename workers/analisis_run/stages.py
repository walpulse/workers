"""Mid-pipeline stage telemetry for analisis_run (RPCs start/finish)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from supabase import Client

# Canonical stage names (worker)
STAGE_OLA1 = "ola1"
STAGE_COMPLIANCE = "compliance"
STAGE_EMPTY_WALLET = "empty_wallet"
STAGE_PORTFOLIO = "portfolio"
STAGE_MULTICHAIN_MODULE = "multichain_module"
STAGE_ORIGINS = "origins"
STAGE_ACTIVITY = "activity"
STAGE_HOPS = "hops"
STAGE_LIGHTS = "lights"
STAGE_SYNTHESIZE = "synthesize"
STAGE_CUSTODY = "custody"
STAGE_PERSIST = "persist"
STAGE_ENTREGABLES = "entregables"


def start_stage(
    sb: Client,
    request_id: str,
    stage: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = (
        sb.rpc(
            "start_analisis_run_stage",
            {
                "p_request_id": request_id,
                "p_stage": stage,
                "p_meta": meta or {},
            },
        )
        .execute()
        .data
    )
    return data if isinstance(data, dict) else {}


def finish_stage(
    sb: Client,
    request_id: str,
    stage: str,
    *,
    status: str = "succeeded",
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = (
        sb.rpc(
            "finish_analisis_run_stage",
            {
                "p_request_id": request_id,
                "p_stage": stage,
                "p_status": status,
                "p_error": error,
                "p_meta": meta or {},
            },
        )
        .execute()
        .data
    )
    return data if isinstance(data, dict) else {}


@contextmanager
def stage(
    sb: Client | None,
    request_id: str | None,
    name: str,
    meta: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Record started→succeeded/failed around a block. No-op if sb/request_id missing."""
    if sb is None or not request_id:
        yield
        return
    start_stage(sb, request_id, name, meta)
    try:
        yield
    except Exception as e:
        finish_stage(sb, request_id, name, status="failed", error=str(e)[:1000])
        raise
    else:
        finish_stage(sb, request_id, name, status="succeeded")
