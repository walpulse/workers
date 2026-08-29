"""On-chain validation: reject EOAs / empty code when RPC is available."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from workers.airdrop_contracts.rpc import resolve_rpc_url


def _rpc_url(blockchain: str, overrides: dict[str, str] | None = None) -> str:
    return resolve_rpc_url(blockchain, overrides)


def eth_get_code(rpc_url: str, address: str) -> str:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getCode",
            "params": [address, "latest"],
        }
    )
    req = Request(
        rpc_url,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "walpulse-airdrop-contracts"},
        method="POST",
    )
    with urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return str(payload.get("result") or "0x")


def has_bytecode(code: str) -> bool:
    c = (code or "").strip().lower()
    return c not in ("", "0x", "0x0")


def validate_rows(
    rows: list[dict[str, Any]],
    *,
    rpc_overrides: dict[str, str] | None = None,
    skip_if_no_rpc: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Returns (accepted, rejected).
    If no RPC for chain and skip_if_no_rpc: keep row (trusted curated / factory path).
    """
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        chain = str(row.get("blockchain") or "")
        address = str(row.get("address") or "")
        rpc = _rpc_url(chain, rpc_overrides)
        if not rpc:
            if skip_if_no_rpc:
                accepted.append(row)
            else:
                rejected.append({**row, "reject_reason": "no_rpc"})
            continue
        try:
            code = eth_get_code(rpc, address)
            if has_bytecode(code):
                accepted.append(row)
            else:
                rejected.append({**row, "reject_reason": "empty_code"})
        except (HTTPError, URLError, RuntimeError, TimeoutError, OSError, ValueError) as exc:
            # Do not drop curated on transient RPC errors
            if row.get("source") == "walpulse_curated":
                accepted.append(row)
            else:
                rejected.append({**row, "reject_reason": f"rpc_error:{exc}"})
    return accepted, rejected
