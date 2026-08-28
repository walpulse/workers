"""Parse CoinGecko API data into token_taxonomy rows."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable

CG_BASE = "https://api.coingecko.com/api/v3"
PER_PAGE = 250
PAGE_SLEEP_S = 0.35
BLUECHIP_MAX_RANK = 100

WALPULSE_TAGS = frozenset({"stable", "meme", "airdrop", "bluechip"})

CATEGORY_TO_TAG: dict[str, str] = {
    "stablecoins": "stable",
    "usd-stablecoin": "stable",
    "fiat-backed-stablecoin": "stable",
    "crypto-backed-stablecoin": "stable",
    "algorithmic-stablecoin": "stable",
    "bridged-stablecoins": "stable",
    "commodity-backed-stablecoin": "stable",
    "meme-token": "meme",
    "dog-themed-coins": "meme",
    "cat-themed-coins": "meme",
    "airdropped-tokens-by-nft-projects": "airdrop",
    "binance-hodler-airdrops": "airdrop",
}

CORE_CATEGORIES = tuple(CATEGORY_TO_TAG.keys())

# CoinGecko asset platform slug → EIP-155 chain_id (v1 EVM; aligned to internal.chains)
COINGECKO_PLATFORM_TO_CHAIN_ID: dict[str, int] = {
    "ethereum": 1,
    "binance-smart-chain": 56,
    "polygon-pos": 137,
    "arbitrum-one": 42161,
    "optimistic-ethereum": 10,
    "base": 8453,
    "avalanche": 43114,
    "fantom": 250,
    "gnosis": 100,
    "linea": 59144,
    "scroll": 534352,
    "celo": 42220,
    "zksync": 324,
    "moonbeam": 1284,
    "moonriver": 1285,
    "cronos": 25,
    "aurora": 1313161554,
    "harmony-shard-0": 1666600000,
    "arbitrum-nova": 42170,
    "blast": 81457,
    "mantle": 5000,
    "opbnb": 204,
    "world-chain": 480,
    "unichain": 130,
    "sonic": 146,
    "sei-v2": 1329,
    "berachain": 80094,
    "zetachain": 7000,
    "ink": 57073,
    "ronin": 2020,
    "canto": 7700,
    "apechain": 33139,
    "megaeth": 4326,
    "monad": 143,
    "hyperevm": 999,
    "plasma": 9745,
    "viction": 88,
    "oasis-sapphire": 23294,
    "emerald": 42262,
    "cronos-zkevm": 388,
    "adi-chain": 36900,
    "redstone": 690,
    "taiko": 167000,
    "polygon-zkevm": 1101,
    "manta-pacific": 169,
    "metis-andromeda": 1088,
    "xdai": 100,
    "boba": 288,
    "kava": 2222,
    "fuse": 122,
    "iotex": 4689,
    "telos": 40,
    "flare-network": 14,
    "core": 1116,
    "klay-token": 8217,
    "pulsechain": 369,
    "mode": 34443,
    "fraxtal": 252,
    "lisk": 1135,
    "soneium": 1868,
    "abstract": 2741,
    "story": 1514,
}


def normalize_evm_address(address: str) -> str | None:
    raw = (address or "").strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", raw):
        return None
    return raw.lower()


def merge_gecko_tags(existing: dict[str, set[str]], gecko_id: str, tag: str) -> None:
    if tag not in WALPULSE_TAGS:
        return
    existing.setdefault(gecko_id, set()).add(tag)


def build_gecko_tag_map(
    category_members: dict[str, list[str]],
    bluechip_ids: list[str],
) -> dict[str, set[str]]:
    """Merge category + bluechip assignments at gecko_id level."""
    out: dict[str, set[str]] = {}

    for category_id, gecko_ids in category_members.items():
        tag = CATEGORY_TO_TAG.get(category_id)
        if not tag:
            continue
        for gecko_id in gecko_ids:
            merge_gecko_tags(out, gecko_id, tag)

    stable_or_meme = {
        gid for gid, tags in out.items() if "stable" in tags or "meme" in tags
    }
    for gecko_id in bluechip_ids:
        if gecko_id in stable_or_meme:
            continue
        merge_gecko_tags(out, gecko_id, "bluechip")

    return out


def expand_platform_rows(
    gecko_tags: dict[str, set[str]],
    platforms_by_gecko: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Expand gecko_id tags to (chain_id, address) rows."""
    rows_by_key: dict[tuple[int, str], dict[str, Any]] = {}
    stats = {"skipped_platform": 0, "skipped_address": 0}

    for gecko_id, tags in gecko_tags.items():
        platforms = platforms_by_gecko.get(gecko_id) or {}
        if not platforms:
            continue
        for platform, address in platforms.items():
            chain_id = COINGECKO_PLATFORM_TO_CHAIN_ID.get(platform)
            if chain_id is None:
                stats["skipped_platform"] += 1
                continue
            normalized = normalize_evm_address(address)
            if normalized is None:
                stats["skipped_address"] += 1
                continue
            key = (chain_id, normalized)
            categories = sorted(tags)
            if key in rows_by_key:
                merged = sorted(set(rows_by_key[key]["categories"]) | set(categories))
                rows_by_key[key]["categories"] = merged
            else:
                rows_by_key[key] = {
                    "chain_id": chain_id,
                    "address": normalized,
                    "categories": categories,
                    "gecko_id": gecko_id,
                }

    return list(rows_by_key.values()), stats


def compute_source_hash(
    category_members: dict[str, list[str]],
    bluechip_ids: list[str],
    list_count: int,
) -> str:
    payload = {
        "list_count": list_count,
        "categories": {k: sorted(v) for k, v in sorted(category_members.items())},
        "bluechip": sorted(bluechip_ids),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_coins_list(payload: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for item in payload:
        gecko_id = str(item.get("id") or "").strip()
        if not gecko_id:
            continue
        platforms = item.get("platforms") or {}
        if isinstance(platforms, dict):
            out[gecko_id] = {
                str(k): str(v) for k, v in platforms.items() if v
            }
    return out


def parse_markets_ids(payload: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for row in payload:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def parse_bluechip_ids(payload: list[dict[str, Any]], max_rank: int = BLUECHIP_MAX_RANK) -> list[str]:
    out: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        gecko_id = row.get("id")
        rank = row.get("market_cap_rank")
        if gecko_id and isinstance(rank, int) and rank <= max_rank:
            out.append(str(gecko_id))
    return out


def fetch_coingecko_json(
    path: str,
    *,
    api_key: str,
    get_json: Callable[[str, dict[str, str]], Any] | None = None,
) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": "walpulse-workers-token-taxonomy/1.0",
        "x-cg-demo-api-key": api_key,
    }
    if get_json is not None:
        return get_json(path, headers)

    url = f"{CG_BASE}{path}"
    for attempt in range(6):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 5:
                time.sleep(2 ** (attempt + 1))
                continue
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"CoinGecko HTTP {exc.code} {path}: {body}") from exc
    raise RuntimeError(f"CoinGecko failed after retries: {path}")


def fetch_category_gecko_ids(category_id: str, api_key: str) -> list[str]:
    page = 1
    ids: list[str] = []
    while True:
        path = (
            f"/coins/markets?vs_currency=usd&category={category_id}"
            f"&per_page={PER_PAGE}&page={page}&sparkline=false"
        )
        try:
            rows = fetch_coingecko_json(path, api_key=api_key)
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return ids
            raise
        if not isinstance(rows, list) or not rows:
            break
        ids.extend(parse_markets_ids(rows))
        if len(rows) < PER_PAGE:
            break
        page += 1
        time.sleep(PAGE_SLEEP_S)
    return ids


def fetch_coins_list(api_key: str) -> list[dict[str, Any]]:
    payload = fetch_coingecko_json("/coins/list?include_platform=true", api_key=api_key)
    if not isinstance(payload, list):
        raise RuntimeError("unexpected /coins/list response")
    return payload


def fetch_bluechip_gecko_ids(api_key: str, max_rank: int = BLUECHIP_MAX_RANK) -> list[str]:
    path = (
        f"/coins/markets?vs_currency=usd&order=market_cap_desc"
        f"&per_page={PER_PAGE}&page=1&sparkline=false"
    )
    rows = fetch_coingecko_json(path, api_key=api_key)
    if not isinstance(rows, list):
        raise RuntimeError("unexpected bluechip markets response")
    return parse_bluechip_ids(rows, max_rank=max_rank)


def collect_token_taxonomy_rows(api_key: str) -> tuple[list[dict[str, Any]], str, dict[str, int]]:
    """Fetch CoinGecko and return (rows, source_hash, stats)."""
    list_payload = fetch_coins_list(api_key)
    platforms_by_gecko = parse_coins_list(list_payload)

    category_members: dict[str, list[str]] = {}
    for category_id in CORE_CATEGORIES:
        category_members[category_id] = fetch_category_gecko_ids(category_id, api_key)

    bluechip_ids = fetch_bluechip_gecko_ids(api_key)
    gecko_tags = build_gecko_tag_map(category_members, bluechip_ids)
    rows, stats = expand_platform_rows(gecko_tags, platforms_by_gecko)
    source_hash = compute_source_hash(category_members, bluechip_ids, len(list_payload))
    return rows, source_hash, stats
