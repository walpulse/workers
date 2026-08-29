"""Parse protocol contract addresses (P0 official seed, P1 Spellbook, P2 DefiLlama)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from workers.spellbook_labels.parse import (
    LABELS_ADDRESSES_REL,
    parse_label_values,
    should_skip_label_file,
)

EVM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
NULL_EVM = "0x0000000000000000000000000000000000000000"

KINDS = frozenset(
    {
        "dex_factory",
        "dex_router",
        "dex_pool",
        "lending",
        "staking",
        "restaking",
        "aggregator",
        "nft_market",
        "permit",
        "other",
    }
)

# Spellbook category → kind (only unambiguous mappings)
SPELLBOOK_CATEGORY_TO_KIND: dict[str, str] = {
    "bridge": "other",  # bridges live in bridge_addresses; skip preferred
    "dex": "dex_router",
    "nft": "nft_market",
    "infrastructure": "other",
}

# Categories we intentionally skip in P1 (owned by other catalogs or noise)
SPELLBOOK_SKIP_CATEGORIES = frozenset({"bridge", "institution", "ofac_sanction", "dao"})

ORIGIN_PRIORITY = {"official": 0, "spellbook": 1, "defillama": 2}

# Static address literals in DefiLlama adapters (P2)
_FACTORY_LIKE = re.compile(
    r"""(?P<key>\b(?:factory|router|vault|pool|lendingPool|comet)\b)\s*[:=]\s*['\"](?P<addr>0x[a-fA-F0-9]{40})['\"]""",
    re.IGNORECASE,
)

DEFAULT_OFFICIAL_SEED = (
    Path(__file__).resolve().parent / "data" / "official_seed.json"
)


def normalize_evm_address(address: str) -> str | None:
    addr = address.strip().lower()
    if not EVM_ADDRESS.match(addr) or addr == NULL_EVM:
        return None
    return addr


def _row(
    *,
    blockchain: str,
    address: str,
    protocol: str,
    kind: str,
    origin: str,
    contract_name: str | None = None,
    source_repo: str | None = None,
    source_commit: str | None = None,
) -> dict[str, Any] | None:
    chain = blockchain.strip().lower()
    addr = normalize_evm_address(address)
    if not chain or not addr:
        return None
    if kind not in KINDS:
        return None
    if origin not in ORIGIN_PRIORITY:
        return None
    return {
        "blockchain": chain,
        "address": addr,
        "protocol": protocol.strip().lower(),
        "kind": kind,
        "origin": origin,
        "contract_name": (contract_name or "").strip() or None,
        "source_repo": (source_repo or "").strip() or None,
        "source_commit": (source_commit or "").strip() or None,
    }


def merge_protocol_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        for row in group:
            key = (row["blockchain"], row["address"])
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = row
                continue
            if ORIGIN_PRIORITY.get(row["origin"], 99) < ORIGIN_PRIORITY.get(
                existing["origin"], 99
            ):
                by_key[key] = row
    return sorted(by_key.values(), key=lambda r: (r["blockchain"], r["address"]))


def load_official_seed(
    path: Path | None = None,
    *,
    source_commit: str | None = None,
) -> list[dict[str, Any]]:
    seed_path = path or DEFAULT_OFFICIAL_SEED
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    entries = payload.get("entries") or []
    rows: list[dict[str, Any]] = []
    for raw in entries:
        row = _row(
            blockchain=str(raw.get("blockchain") or ""),
            address=str(raw.get("address") or ""),
            protocol=str(raw.get("protocol") or ""),
            kind=str(raw.get("kind") or ""),
            origin="official",
            contract_name=raw.get("contract_name"),
            source_repo=raw.get("source_repo") or payload.get("source_repo"),
            source_commit=source_commit or raw.get("source_commit"),
        )
        if row:
            rows.append(row)
    return rows


def collect_spellbook_protocol_rows(
    labels_dir: Path,
    *,
    source_commit: str | None = None,
) -> list[dict[str, Any]]:
    """P1: VALUES-only Spellbook labels mapped to protocol kinds."""
    if not labels_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for sql_path in sorted(labels_dir.rglob("*.sql")):
        if should_skip_label_file(sql_path):
            continue
        text = sql_path.read_text(encoding="utf-8", errors="replace")
        for label in parse_label_values(text):
            category = (label.get("category") or "").strip().lower()
            if category in SPELLBOOK_SKIP_CATEGORIES:
                continue
            kind = SPELLBOOK_CATEGORY_TO_KIND.get(category)
            if not kind:
                continue
            name = (label.get("name") or sql_path.stem).strip()
            protocol = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:64] or category
            row = _row(
                blockchain=str(label.get("blockchain") or ""),
                address=str(label.get("address") or ""),
                protocol=protocol,
                kind=kind,
                origin="spellbook",
                contract_name=name,
                source_repo="duneanalytics/spellbook",
                source_commit=source_commit,
            )
            if row:
                rows.append(row)
    return rows


def collect_defillama_protocol_rows(
    projects_dir: Path,
    *,
    allowlist: set[str] | None = None,
    source_commit: str | None = None,
) -> list[dict[str, Any]]:
    """P2: extract static factory/router literals from DefiLlama-Adapters projects/."""
    if not projects_dir.is_dir():
        return []
    allow = {a.lower() for a in allowlist} if allowlist else None
    rows: list[dict[str, Any]] = []
    for project_dir in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        slug = project_dir.name.lower()
        if allow is not None and slug not in allow:
            continue
        for js_path in project_dir.rglob("*.js"):
            if "node_modules" in js_path.parts:
                continue
            text = js_path.read_text(encoding="utf-8", errors="replace")
            for m in _FACTORY_LIKE.finditer(text):
                key = m.group("key").lower()
                kind = "dex_factory" if "factory" in key else (
                    "dex_router" if "router" in key else (
                        "lending" if "lend" in key or "comet" in key else "other"
                    )
                )
                if key == "vault":
                    kind = "other"
                row = _row(
                    blockchain="ethereum",
                    address=m.group("addr"),
                    protocol=slug,
                    kind=kind,
                    origin="defillama",
                    contract_name=f"{slug}:{key}",
                    source_repo="DefiLlama/DefiLlama-Adapters",
                    source_commit=source_commit,
                )
                if row:
                    rows.append(row)
    return rows


def collect_protocol_rows(
    *,
    official_seed_path: Path | None = None,
    official_commit: str | None = None,
    spellbook_labels_dir: Path | None = None,
    spellbook_commit: str | None = None,
    defillama_projects_dir: Path | None = None,
    defillama_commit: str | None = None,
    defillama_allowlist: set[str] | None = None,
    layers: set[str] | None = None,
) -> list[dict[str, Any]]:
    active = layers or {"p0"}
    groups: list[list[dict[str, Any]]] = []
    if "p0" in active:
        groups.append(
            load_official_seed(official_seed_path, source_commit=official_commit)
        )
    if "p1" in active and spellbook_labels_dir is not None:
        groups.append(
            collect_spellbook_protocol_rows(
                spellbook_labels_dir, source_commit=spellbook_commit
            )
        )
    if "p2" in active and defillama_projects_dir is not None:
        groups.append(
            collect_defillama_protocol_rows(
                defillama_projects_dir,
                allowlist=defillama_allowlist,
                source_commit=defillama_commit,
            )
        )
    return merge_protocol_rows(*groups)


__all__ = [
    "DEFAULT_OFFICIAL_SEED",
    "LABELS_ADDRESSES_REL",
    "collect_defillama_protocol_rows",
    "collect_protocol_rows",
    "collect_spellbook_protocol_rows",
    "load_official_seed",
    "merge_protocol_rows",
]
