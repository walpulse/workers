"""Discover Sablier airdrop campaigns via official Envio GraphQL indexer.

Replaces Alchemy eth_getLogs factory scans (see ADR 2026-09-14).
Endpoint: https://docs.sablier.com/api/airdrops/indexers
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from workers.airdrop_contracts.parse_factories import load_factories_config

PKG_DIR = Path(__file__).resolve().parent
DEFAULT_FACTORIES_PATH = PKG_DIR / "factories.yaml"

ENVIO_ENDPOINT_DEFAULT = "https://indexer.hyperindex.xyz/508d217/v1/graphql"
PAGE_SIZE_DEFAULT = 500

# EVM chainId (string from Envio) → Walpulse blockchain slug.
CHAIN_ID_TO_SLUG: dict[str, str] = {
    "1": "ethereum",
    "10": "optimism",
    "56": "bnb",
    "100": "gnosis",
    "137": "polygon",
    "324": "zksync",
    "8453": "base",
    "42161": "arbitrum",
    "43114": "avalanche_c",
    "534352": "scroll",
    "59144": "linea",
}

CAMPAIGNS_QUERY = """
query($addrs: [String!]!, $limit: Int!, $offset: Int!) {
  Campaign(
    where: { factory: { address: { _in: $addrs } } }
    limit: $limit
    offset: $offset
    order_by: { timestamp: asc }
  ) {
    id
    address
    chainId
    timestamp
    factory { address }
    asset { symbol address }
  }
}
"""


def _norm_addr(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text.startswith("0x") or len(text) != 42:
        return None
    try:
        int(text[2:], 16)
    except ValueError:
        return None
    return text


def envio_endpoint() -> str:
    return (os.environ.get("SABLIER_ENVIO_URL") or ENVIO_ENDPOINT_DEFAULT).strip()


def _page_size() -> int:
    raw = (os.environ.get("SABLIER_ENVIO_PAGE_SIZE") or "").strip()
    if raw.isdigit():
        return max(50, min(1000, int(raw)))
    return PAGE_SIZE_DEFAULT


def graphql(query: str, variables: dict[str, Any], *, endpoint: str | None = None) -> dict[str, Any]:
    url = (endpoint or envio_endpoint()).strip()
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "walpulse-airdrop-contracts",
        },
        method="POST",
    )
    with urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(f"Envio GraphQL errors: {payload['errors']}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Envio GraphQL missing data")
    return data


def fetch_campaigns_for_factories(
    factory_addresses: list[str],
    *,
    endpoint: str | None = None,
    page_size: int | None = None,
) -> list[dict[str, Any]]:
    """Paginate Campaign rows whose factory.address is in the allowlist."""
    addrs = sorted({a for a in (_norm_addr(x) for x in factory_addresses) if a})
    if not addrs:
        return []
    size = page_size or _page_size()
    out: list[dict[str, Any]] = []
    offset = 0
    while True:
        data = graphql(
            CAMPAIGNS_QUERY,
            {"addrs": addrs, "limit": size, "offset": offset},
            endpoint=endpoint,
        )
        batch = data.get("Campaign") or []
        if not isinstance(batch, list):
            raise RuntimeError("Envio Campaign response is not a list")
        out.extend(batch)
        if len(batch) < size:
            break
        offset += size
    return out


def campaign_to_row(
    campaign: dict[str, Any],
    *,
    factory_meta: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    address = _norm_addr(campaign.get("address"))
    factory_addr = _norm_addr((campaign.get("factory") or {}).get("address"))
    chain_id = str(campaign.get("chainId") or "").strip()
    blockchain = CHAIN_ID_TO_SLUG.get(chain_id)
    if not address or not factory_addr or not blockchain:
        return None
    meta = factory_meta.get(factory_addr) or {}
    # Prefer Envio chainId mapping; drop if factory yaml chain disagrees.
    yaml_chain = str(meta.get("blockchain") or "").strip().lower()
    if yaml_chain and yaml_chain != blockchain:
        return None
    asset = campaign.get("asset") or {}
    token_address = _norm_addr(asset.get("address"))
    token_symbol = asset.get("symbol")
    if token_symbol is not None:
        token_symbol = str(token_symbol).strip() or None
    slug = str(meta.get("project_slug") or "sablier").strip()
    name = str(meta.get("project_name") or "Sablier Airdrops").strip()
    return {
        "blockchain": blockchain,
        "address": address,
        "project_slug": slug,
        "project_name": name,
        "token_address": token_address,
        "token_symbol": token_symbol,
        "source": "factory_clone",
        "factory_address": factory_addr,
        "notes": f"sablier envio campaign {campaign.get('id')}",
        "raw": {
            "envio": {
                "id": campaign.get("id"),
                "chain_id": chain_id,
                "timestamp": campaign.get("timestamp"),
                "factory": factory_addr,
            }
        },
    }


def collect_envio_clones(
    *,
    factories_path: Path | None = None,
    endpoint: str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Fetch all allowlisted Sablier campaigns from Envio.

    Returns (rows, warnings). Rows are a full replace set for source=factory_clone
    (no block cursors).
    """
    cfg = load_factories_config(factories_path or DEFAULT_FACTORIES_PATH)
    factories = cfg.get("factories") or []
    factory_meta: dict[str, dict[str, Any]] = {}
    addrs: list[str] = []
    for factory in factories:
        if not isinstance(factory, dict):
            continue
        addr = _norm_addr(factory.get("address"))
        if not addr:
            continue
        addrs.append(addr)
        factory_meta[addr] = factory

    warnings: list[str] = []
    if not addrs:
        warnings.append("factories.yaml has no valid factory addresses")
        return [], warnings

    try:
        campaigns = fetch_campaigns_for_factories(addrs, endpoint=endpoint)
    except (HTTPError, URLError, RuntimeError, TimeoutError, OSError, ValueError) as exc:
        warnings.append(f"envio_fetch_failed: {exc}")
        return [], warnings

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    skipped = 0
    for camp in campaigns:
        if not isinstance(camp, dict):
            skipped += 1
            continue
        row = campaign_to_row(camp, factory_meta=factory_meta)
        if not row:
            skipped += 1
            continue
        key = f"{row['blockchain']}:{row['address']}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    if skipped:
        warnings.append(f"envio_skipped_campaigns={skipped}")
    print(
        f"  envio campaigns fetched={len(campaigns)} rows={len(rows)} "
        f"factories={len(addrs)}",
        flush=True,
    )
    return rows, warnings


# Re-export unused; keep parse_factories.load_factories_config as source of truth.