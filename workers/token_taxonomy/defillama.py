"""DefiLlama stablecoins — API + peggedassets-server parse for token_taxonomy v1.1."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from workers.token_taxonomy.parse import expand_platform_rows, normalize_evm_address

DL_STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoins?includePrices=false"
DL_CHAINS_URL = "https://api.llama.fi/chains"
PEGGEDASSETS_REPO = "DefiLlama/peggedassets-server"
SPARSE_PATH = "src/adapters/peggedAssets"

EXCLUDED_PEG = frozenset({"peggedVAR"})
INCLUDE_CONTRACT_KEYS = ("issued",)
BRIDGED_PREFIX = "bridgedfrom"
EXCLUDE_KEY_PREFIXES = ("bridgeon", "unreleased")
EVM_RE = re.compile(r"0x[a-fA-F0-9]{40}")

RowKey = tuple[int, str]

SLUG_CHAIN_ID_ALIASES: dict[str, int] = {
    "bsc": 56,
    "avax": 43114,
    "polygon": 137,
    "ethereum": 1,
    "arbitrum": 42161,
    "optimism": 10,
    "base": 8453,
    "fantom": 250,
    "xdai": 100,
    "gnosis": 100,
    "celo": 42220,
    "moonbeam": 1284,
    "moonriver": 1285,
    "aurora": 1313161554,
    "harmony": 1666600000,
    "cronos": 25,
    "metis": 1088,
    "linea": 59144,
    "scroll": 534352,
    "mantle": 5000,
    "blast": 81457,
    "zksync": 324,
    "era": 324,
    "polygon_zkevm": 1101,
    "arbitrum_nova": 42170,
    "boba": 288,
    "kava": 2222,
    "fuse": 122,
    "iotex": 4689,
    "telos": 40,
    "flare": 14,
    "core": 1116,
    "klaytn": 8217,
    "pulse": 369,
    "mode": 34443,
    "fraxtal": 252,
    "lisk": 1135,
    "soneium": 1868,
    "abstract": 2741,
    "sonic": 146,
    "worldchain": 480,
    "unichain": 130,
    "sei": 1329,
    "berachain": 80094,
    "zetachain": 7000,
    "ink": 57073,
    "ronin": 2020,
    "canto": 7700,
    "taiko": 167000,
    "manta": 169,
    "redstone": 690,
    "hyperevm": 999,
    "hyperliquid": 999,
    "plasma": 9745,
    "viction": 88,
    "cronos_zkevm": 388,
    "adi_chain": 36900,
    "opbnb": 204,
    "apechain": 33139,
    "monad": 143,
    "megaeth": 4326,
    "rsk": 30,
    "rootstock": 30,
    "okexchain": 66,
    "okc": 66,
    "heco": 128,
    "tomochain": 88,
    "wanchain": 888,
    "milkomeda": 2001,
    "elastos": 20,
    "evmos": 9001,
    "astar": 592,
    "theta": 361,
    "syscoin": 57,
    "reinetwork": 47805,
    "loopring": 1135,
    "dfk": 53935,
    "karura": 686,
    "sx": 416,
    "ethereumclassic": 61,
    "wan": 888,
    "defichain": 1130,
    "dogechain": 2000,
    "kardia": 24,
    "thundercore": 108,
    "kujira": 1100,
    "waves": 87,
    "immutablex": 13371,
    "imx": 13371,
    "plume_mainnet": 98866,
    "katana": 747474,
    "etlk": 42793,
    "rbn": 1514,
    "mantra": 5888,
    "corn": 21000000,
    "xlayer": 196,
    "xdc": 50,
    "nero": 1689,
    "perennial": 60808,
    "shape": 360,
    "btr": 200901,
    "galxe": 1261120,
    "vitruveo": 1490,
    "zkfair": 42766,
    "wemix": 1111,
    "kroma": 255,
    "bsquared": 223,
    "bob": 60808,
    "occ": 151,
    "morph": 2818,
    "flow": 747,
    "injective": 1776,
    "move": 3073,
    "ontology": 58,
    "nibiru": 6900,
    "oasis": 42262,
    "crab": 44,
    "meter": 82,
    "sxnetwork": 416,
}


def _http_get_json(url: str, *, label: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "walpulse-workers-token-taxonomy/1.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"{label} HTTP {exc.code}: {body}") from exc


def is_fiat_peg(peg_type: str | None) -> bool:
    if not peg_type:
        return False
    if peg_type in EXCLUDED_PEG:
        return False
    return peg_type.startswith("pegged")


def filter_fiat_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in assets if is_fiat_peg(a.get("pegType"))]


def build_slug_to_chain_id(chains_payload: list[dict[str, Any]]) -> dict[str, int]:
    out = dict(SLUG_CHAIN_ID_ALIASES)
    for row in chains_payload:
        chain_id = row.get("chainId")
        if not isinstance(chain_id, int) or chain_id <= 0:
            continue
        gecko_id = (row.get("gecko_id") or "").strip().lower()
        name = (row.get("name") or "").strip().lower()
        if gecko_id:
            out[gecko_id] = chain_id
        if name:
            out[name.replace(" ", "_")] = chain_id
            out[name.replace(" ", "")] = chain_id
            if name == "bsc":
                out["bsc"] = chain_id
            if name == "op mainnet":
                out["optimism"] = chain_id
    return out


def _api_fingerprint(fiat_assets: list[dict[str, Any]]) -> str:
    payload = [
        {
            "id": a.get("id"),
            "gecko_id": a.get("gecko_id"),
            "pegType": a.get("pegType"),
        }
        for a in sorted(fiat_assets, key=lambda x: str(x.get("id") or ""))
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_defillama_stablecoins() -> tuple[list[dict[str, Any]], dict[str, int], str]:
    """Return (fiat assets, slug→chain_id map, api fingerprint)."""
    stable_payload = _http_get_json(DL_STABLECOINS_URL, label="defillama/stablecoins")
    chains_payload = _http_get_json(DL_CHAINS_URL, label="defillama/chains")
    assets = stable_payload.get("peggedAssets") or []
    fiat = filter_fiat_assets(assets)
    slug_map = build_slug_to_chain_id(chains_payload if isinstance(chains_payload, list) else [])
    return fiat, slug_map, _api_fingerprint(fiat)


def _row_key(chain_id: int, address: str) -> RowKey:
    return (chain_id, address.lower())


def _merge_dl_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[RowKey, dict[str, Any]] = {}
    for rows in groups:
        for r in rows:
            k = _row_key(int(r["chain_id"]), str(r["address"]))
            if k in merged:
                cats = sorted(set(merged[k]["categories"]) | set(r["categories"]))
                merged[k]["categories"] = cats
                if not merged[k].get("gecko_id") and r.get("gecko_id"):
                    merged[k]["gecko_id"] = r["gecko_id"]
            else:
                merged[k] = {
                    "chain_id": k[0],
                    "address": k[1],
                    "categories": sorted(set(r["categories"])),
                    "gecko_id": r.get("gecko_id") or "",
                }
    return list(merged.values())


def _extract_chain_contracts_block(text: str) -> str | None:
    m = re.search(r"chainContracts\s*(?::\s*\w+\s*)?=\s*\{", text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_addresses_from_chain_block(block: str) -> tuple[list[str], dict[str, int]]:
    addresses: list[str] = []
    excluded: Counter[str] = Counter()
    active_include = False
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        key_m = re.match(r"([a-zA-Z0-9_]+)\s*:", stripped)
        if key_m:
            key = key_m.group(1).lower()
            if any(key.startswith(p) for p in EXCLUDE_KEY_PREFIXES):
                excluded[key.split("[")[0]] += len(EVM_RE.findall(stripped))
                active_include = False
                continue
            if key in INCLUDE_CONTRACT_KEYS or key.startswith(BRIDGED_PREFIX):
                active_include = True
                for addr in EVM_RE.findall(stripped):
                    norm = normalize_evm_address(addr)
                    if norm:
                        addresses.append(norm)
            elif key.startswith("bridge"):
                excluded["bridge"] += len(EVM_RE.findall(stripped))
                active_include = False
            else:
                active_include = False
        elif active_include:
            for addr in EVM_RE.findall(stripped):
                norm = normalize_evm_address(addr)
                if norm:
                    addresses.append(norm)
    return addresses, dict(excluded)


def parse_adapter_file(
    text: str,
    slug_map: dict[str, int],
    gecko_id: str,
    *,
    allowed: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    block = _extract_chain_contracts_block(text)
    stats: dict[str, Any] = {
        "parse_ok": bool(block),
        "unmapped_slugs": Counter(),
        "excluded_addrs": Counter(),
    }
    if not block or not allowed:
        return [], stats

    rows: list[dict[str, Any]] = []
    chain_pat = re.compile(r"^\s{2}([a-zA-Z0-9_]+):\s*\{", re.MULTILINE)
    matches = list(chain_pat.finditer(block))
    for idx, m in enumerate(matches):
        slug = m.group(1).lower()
        start = m.end() - 1
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block) - 1
        chain_block = block[start:end]
        addrs, excl = _parse_addresses_from_chain_block(chain_block)
        stats["excluded_addrs"].update(excl)
        chain_id = slug_map.get(slug)
        if chain_id is None or chain_id <= 0:
            stats["unmapped_slugs"][slug] += len(addrs)
            continue
        for addr in addrs:
            rows.append(
                {
                    "chain_id": chain_id,
                    "address": addr,
                    "categories": ["stable"],
                    "gecko_id": gecko_id,
                }
            )
    return rows, stats


def parse_peggedassets_rows(
    adapters_root: Path,
    fiat_assets: list[dict[str, Any]],
    slug_map: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    allowed_gecko = {str(a["gecko_id"]).strip() for a in fiat_assets if a.get("gecko_id")}
    api_by_gecko = {
        str(a.get("gecko_id") or "").strip(): a for a in fiat_assets if a.get("gecko_id")
    }
    all_rows: list[dict[str, Any]] = []
    unmapped: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    parse_errors: list[str] = []
    adapter_counts: Counter[str] = Counter()
    no_gecko_parsed = 0

    for adapter_dir in sorted(adapters_root.iterdir()):
        if not adapter_dir.is_dir():
            continue
        gecko_id = adapter_dir.name
        config = adapter_dir / "config.ts"
        index = adapter_dir / "index.ts"
        src_file = config if config.is_file() else (index if index.is_file() else None)
        if not src_file:
            continue
        text = src_file.read_text(encoding="utf-8", errors="replace")
        allowed = gecko_id in allowed_gecko
        if not allowed and gecko_id not in api_by_gecko:
            no_gecko_parsed += 1
            allowed = True

        rows, st = parse_adapter_file(text, slug_map, gecko_id, allowed=allowed)
        all_rows.extend(rows)
        unmapped.update(st.get("unmapped_slugs") or {})
        excluded.update(st.get("excluded_addrs") or {})
        if not st.get("parse_ok"):
            parse_errors.append(gecko_id)
        adapter_counts[gecko_id] = len(rows)

    merged = _merge_dl_rows(all_rows)
    stats = {
        "adapters_scanned": sum(1 for d in adapters_root.iterdir() if d.is_dir()),
        "adapters_with_rows": sum(1 for _, n in adapter_counts.items() if n > 0),
        "parse_errors": len(parse_errors),
        "unmapped_slugs": dict(unmapped.most_common(20)),
        "excluded_addr_counts": dict(excluded),
        "dl_no_gecko_adapters_parsed": no_gecko_parsed,
        "git_rows": len(merged),
    }
    return merged, stats


def expand_dl_gecko_gap_rows(
    fiat_assets: list[dict[str, Any]],
    platforms_by_gecko: dict[str, dict[str, str]],
    gecko_ids_with_rows: set[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    gecko_ids = sorted(
        {str(a["gecko_id"]).strip() for a in fiat_assets if a.get("gecko_id")}
        - gecko_ids_with_rows
    )
    gecko_tags = {gid: {"stable"} for gid in gecko_ids}
    rows, stats = expand_platform_rows(gecko_tags, platforms_by_gecko)
    for r in rows:
        if "stable" not in r["categories"]:
            r["categories"] = sorted(set(r["categories"]) | {"stable"})
    return rows, stats


def collect_defillama_stable_rows(
    adapters_root: Path,
    platforms_by_gecko: dict[str, dict[str, str]],
    *,
    fiat_assets: list[dict[str, Any]] | None = None,
    slug_map: dict[str, int] | None = None,
    api_fingerprint: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Hybrid scenario C: git chainContracts + CG expand for gecko gaps."""
    if fiat_assets is None or slug_map is None or api_fingerprint is None:
        fiat_assets, slug_map, api_fingerprint = fetch_defillama_stablecoins()

    rows_b, stats_b = parse_peggedassets_rows(adapters_root, fiat_assets, slug_map)
    gecko_b = {r["gecko_id"] for r in rows_b if r.get("gecko_id")}
    rows_a, stats_a = expand_dl_gecko_gap_rows(fiat_assets, platforms_by_gecko, gecko_b)
    rows = _merge_dl_rows(rows_b, rows_a)

    stats = {
        **stats_b,
        "gap_rows": len(rows_a),
        "dl_stable_rows": len(rows),
        "dl_gecko_gaps_expanded": stats_a,
        "defillama_api_fingerprint": api_fingerprint,
    }
    return rows, stats
