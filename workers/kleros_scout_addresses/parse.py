"""Parse Kleros Scout Curate litems into Walpulse catalog rows."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

REGISTRY_ADDRESS_TAG = "0x66260c69d03837016d88c9877e61e08ef74c59f2"
REGISTRY_TOKEN = "0x70533554fe5c17caf77fe530f77eab933b92af60"
REGISTRY_CONTRACT_DOMAIN = "0x957a53a994860be4750810131d9c876b2f52d6e1"

REGISTRIES: dict[str, str] = {
    REGISTRY_ADDRESS_TAG: "address_tag",
    REGISTRY_TOKEN: "token",
    REGISTRY_CONTRACT_DOMAIN: "contract_domain",
}

ACTIVE_STATUSES = frozenset({"Registered", "ClearingRequested"})


def parse_caip10(key0: str) -> tuple[int, str] | None:
    """Parse eip155:{chainId}:{address} CAIP-10. Returns (chain_id, lowercase address)."""
    raw = (key0 or "").strip()
    if not raw.lower().startswith("eip155:"):
        return None
    parts = raw.split(":", 2)
    if len(parts) != 3:
        return None
    _, chain_part, addr_part = parts
    if not chain_part.isdigit():
        return None
    addr = addr_part.strip()
    if addr.lower().startswith("0x"):
        addr = "0x" + addr[2:].lower()
        if len(addr) != 42:
            return None
    elif not addr:
        return None
    return int(chain_part), addr


def _resolution_iso(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    try:
        ts = int(str(raw))
    except ValueError:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def normalize_item(raw: dict[str, Any], registry: str) -> dict[str, Any] | None:
    status = str(raw.get("status") or "").strip()
    if status not in ACTIVE_STATUSES:
        return None

    key0 = str(raw.get("key0") or "")
    parsed = parse_caip10(key0)
    if parsed is None:
        return None
    chain_id, address = parsed

    key1 = str(raw.get("key1") or "").strip()
    key2 = str(raw.get("key2") or "").strip()
    key3 = str(raw.get("key3") or "").strip() if raw.get("key3") is not None else ""

    item_id = str(raw.get("itemID") or raw.get("item_id") or "").strip()
    if not item_id or not key1:
        return None

    if registry == "address_tag":
        project_name = key2
        name_tag = key1
        website = key3 or None
    elif registry == "token":
        project_name = key2
        name_tag = key1
        website = None
    elif registry == "contract_domain":
        project_name = ""
        name_tag = key1
        website = None
    else:
        return None

    return {
        "chain_id": chain_id,
        "address": address,
        "registry": registry,
        "project_name": project_name,
        "name_tag": name_tag,
        "website": website,
        "item_id": item_id,
        "status": status,
        "source_updated_at": _resolution_iso(raw.get("latestRequestResolutionTime")),
    }


def collect_kleros_scout_rows(
    items_by_registry: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    seen: set[tuple[int, str, str]] = set()
    rows: list[dict[str, Any]] = []

    for registry, items in items_by_registry.items():
        for raw in items:
            row = normalize_item(raw, registry)
            if row is None:
                continue
            key = (row["chain_id"], row["address"], row["registry"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    rows.sort(key=lambda r: (r["registry"], r["chain_id"], r["address"]))
    return rows


def compute_source_hash(items_by_registry: dict[str, list[dict[str, Any]]]) -> str:
    """Fingerprint: sorted (registry, itemID, resolutionTime) tuples."""
    tuples: list[tuple[str, str, str]] = []
    for registry, items in sorted(items_by_registry.items()):
        for raw in items:
            status = str(raw.get("status") or "").strip()
            if status not in ACTIVE_STATUSES:
                continue
            item_id = str(raw.get("itemID") or raw.get("item_id") or "").strip()
            if not item_id:
                continue
            resolution = str(raw.get("latestRequestResolutionTime") or "")
            tuples.append((registry, item_id, resolution))
    tuples.sort()
    payload = json.dumps(tuples, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
