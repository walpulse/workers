"""Best-effort Spellbook _sector/airdrops metadata for enrichment."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

JINJA_TOKEN = re.compile(
    r"\{%\s*set\s+(\w+)\s*=\s*'(0x[a-fA-F0-9]{40})'\s*%\}",
    re.IGNORECASE,
)
EVENT_SOURCE = re.compile(
    r"\{\{\s*source\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)\s*\}\}"
)


def parse_claim_sql(path: Path, text: str) -> dict[str, Any] | None:
    parts = path.as_posix().split("/")
    if "_sector/airdrops" not in path.as_posix() and "airdrops" not in parts:
        return None
    try:
        airdrops_idx = parts.index("airdrops")
        chain = parts[airdrops_idx + 1]
    except (ValueError, IndexError):
        chain = "ethereum"
    fname = path.name
    if not fname.endswith("_claims.sql"):
        return None
    slug = fname.replace("_airdrop_claims.sql", "").replace("_airdrop_1_claims.sql", "")
    for suffix in (
        "_ethereum",
        "_optimism",
        "_arbitrum",
        "_bnb",
        "_gnosis",
        "_avalanche_c",
        "_zksync",
        "_base",
        "_polygon",
        "_scroll",
        "_linea",
    ):
        if slug.endswith(suffix):
            slug = slug[: -len(suffix)]
            break
    token_address = None
    for var, addr in JINJA_TOKEN.findall(text):
        if "token" in var.lower():
            token_address = addr.lower()
            break
    ev = EVENT_SOURCE.search(text)
    return {
        "blockchain": chain.lower(),
        "project_slug": slug,
        "token_address": token_address,
        "event_source": ev.group(1) if ev else None,
        "event_table": ev.group(2) if ev else None,
        "spellbook_path": path.as_posix(),
    }


def collect_spellbook_metadata(repo_root: Path) -> dict[str, dict[str, Any]]:
    """
    Index metadata by project_slug (and slug@chain).
    Does not produce claim addresses.
    """
    root = repo_root
    candidates = [
        root / "models" / "_sector" / "airdrops",
        root / "dbt_subprojects" / "daily_spellbook" / "models" / "_sector" / "airdrops",
    ]
    base = next((c for c in candidates if c.is_dir()), None)
    index: dict[str, dict[str, Any]] = {}
    if base is None:
        return index
    for path in base.rglob("*_claims.sql"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        meta = parse_claim_sql(path.relative_to(root) if root in path.parents else path, text)
        if not meta:
            continue
        slug = meta["project_slug"]
        index[slug] = meta
        index[f"{slug}@{meta['blockchain']}"] = meta
    return index


def enrich_rows_with_spellbook(
    rows: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not metadata:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        slug = str(row.get("project_slug") or "")
        chain = str(row.get("blockchain") or "")
        meta = metadata.get(f"{slug}@{chain}") or metadata.get(slug)
        if meta:
            raw = dict(enriched.get("raw") or {})
            raw["spellbook"] = {
                "path": meta.get("spellbook_path"),
                "event_source": meta.get("event_source"),
                "event_table": meta.get("event_table"),
            }
            enriched["raw"] = raw
            if not enriched.get("token_address") and meta.get("token_address"):
                enriched["token_address"] = meta["token_address"]
        out.append(enriched)
    return out
