"""Merge curated + factory clones; curated wins on (blockchain, address)."""

from __future__ import annotations

from typing import Any

SOURCE_PRIORITY = {
    "walpulse_curated": 2,
    "factory_clone": 1,
}


def merge_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        for row in group:
            key = (str(row["blockchain"]), str(row["address"]).lower())
            prev = best.get(key)
            if prev is None:
                best[key] = row
                continue
            p_prev = SOURCE_PRIORITY.get(str(prev.get("source")), 0)
            p_new = SOURCE_PRIORITY.get(str(row.get("source")), 0)
            if p_new > p_prev:
                # Keep enrichment from lower priority if useful
                merged = dict(row)
                if not merged.get("token_address") and prev.get("token_address"):
                    merged["token_address"] = prev["token_address"]
                if not merged.get("token_symbol") and prev.get("token_symbol"):
                    merged["token_symbol"] = prev["token_symbol"]
                best[key] = merged
            elif p_new == p_prev:
                # Prefer row with more token metadata
                if not prev.get("token_address") and row.get("token_address"):
                    best[key] = row
    return sorted(best.values(), key=lambda r: (r["blockchain"], r["address"]))
