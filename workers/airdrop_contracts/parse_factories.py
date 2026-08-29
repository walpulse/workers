"""Discover Sablier (etc.) airdrop campaign clones via factory Create* logs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

from workers.airdrop_contracts.rpc import resolve_rpc_url

PKG_DIR = Path(__file__).resolve().parent
DEFAULT_FACTORIES_PATH = PKG_DIR / "factories.yaml"

# Alchemy Free caps eth_getLogs at 10 blocks; PAYG is unlimited on major chains.
# Start larger and shrink on 400; override with AIRDROP_FACTORY_LOG_CHUNK.
LOG_CHUNK_DEFAULT = 2_000
LOG_CHUNK_MIN = 10
# First touch without cursor: only look back N blocks (full history → --force + PAYG).
BOOTSTRAP_BLOCKS_DEFAULT = 5_000


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


def _topic_to_address(topic: str) -> str | None:
    t = topic.lower().removeprefix("0x")
    if len(t) != 64:
        return None
    return _norm_addr("0x" + t[-40:])


def load_factories_config(path: Path | None = None) -> dict[str, Any]:
    yaml_path = path or DEFAULT_FACTORIES_PATH
    return yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}


def rpc_call(rpc_url: str, method: str, params: list[Any]) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    req = Request(
        rpc_url,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "walpulse-airdrop-contracts"},
        method="POST",
    )
    with urlopen(req, timeout=90) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(f"RPC error: {payload['error']}")
    return payload.get("result")


def eth_block_number(rpc_url: str) -> int:
    return int(rpc_call(rpc_url, "eth_blockNumber", []), 16)


def eth_get_logs(
    rpc_url: str,
    *,
    address: str,
    topics: list[str],
    from_block: int,
    to_block: int,
) -> list[dict[str, Any]]:
    params = {
        "address": address,
        "topics": [topics],
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
    }
    try:
        result = rpc_call(rpc_url, "eth_getLogs", [params])
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001
            detail = str(exc.reason or "")
        raise HTTPError(exc.url, exc.code, f"{exc.reason} {detail}".strip(), exc.headers, None) from None
    if not isinstance(result, list):
        return []
    return result


def _log_chunk_size() -> int:
    raw = (os.environ.get("AIRDROP_FACTORY_LOG_CHUNK") or "").strip()
    if raw.isdigit():
        return max(LOG_CHUNK_MIN, int(raw))
    return LOG_CHUNK_DEFAULT


def _bootstrap_blocks() -> int:
    raw = (os.environ.get("AIRDROP_FACTORY_BOOTSTRAP_BLOCKS") or "").strip()
    if raw.isdigit():
        return max(0, int(raw))
    return BOOTSTRAP_BLOCKS_DEFAULT


def fetch_logs_adaptive(
    rpc_url: str,
    *,
    address: str,
    topics: list[str],
    from_block: int,
    to_block: int,
) -> list[dict[str, Any]]:
    """Paginate getLogs; shrink chunk on HTTP 400 (Alchemy Free = 10-block cap)."""
    chunk_size = _log_chunk_size()
    cursor = from_block
    out: list[dict[str, Any]] = []
    while cursor <= to_block:
        end = min(cursor + chunk_size - 1, to_block)
        try:
            out.extend(
                eth_get_logs(
                    rpc_url,
                    address=address,
                    topics=topics,
                    from_block=cursor,
                    to_block=end,
                )
            )
            cursor = end + 1
        except HTTPError as exc:
            if exc.code in (400, 413) and chunk_size > LOG_CHUNK_MIN:
                chunk_size = max(LOG_CHUNK_MIN, chunk_size // 2)
                print(
                    f"    getLogs range too wide → chunk={chunk_size} "
                    f"(retry @{cursor})",
                    flush=True,
                )
                continue
            raise
    return out


def parse_factory_clones_from_logs(
    logs: list[dict[str, Any]],
    *,
    factory: dict[str, Any],
) -> list[dict[str, Any]]:
    factory_addr = _norm_addr(factory.get("address"))
    blockchain = str(factory.get("blockchain") or "").strip().lower()
    slug = str(factory.get("project_slug") or "sablier").strip()
    name = str(factory.get("project_name") or "Sablier Airdrops").strip()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for log in logs:
        topics = log.get("topics") or []
        if len(topics) < 2:
            continue
        campaign = _topic_to_address(str(topics[1]))
        if not campaign or campaign in seen:
            continue
        seen.add(campaign)
        out.append(
            {
                "blockchain": blockchain,
                "address": campaign,
                "project_slug": slug,
                "project_name": name,
                "token_address": None,
                "token_symbol": None,
                "source": "factory_clone",
                "factory_address": factory_addr,
                "notes": f"{factory.get('family')} {factory.get('version')} campaign",
                "raw": {
                    "factory": factory_addr,
                    "tx": log.get("transactionHash"),
                    "block": log.get("blockNumber"),
                    "topic0": topics[0],
                },
            }
        )
    return out


def _cursor_key(blockchain: str, factory_address: str) -> str:
    return f"{blockchain}:{factory_address.lower()}"


def collect_factory_clones(
    *,
    factories_path: Path | None = None,
    rpc_overrides: dict[str, str] | None = None,
    max_blocks_per_factory: int | None = None,
    cursors: dict[str, int] | None = None,
    force_full_rescan: bool = False,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """
    Scan factory Create* logs.

    Returns (new_rows, warnings, cursor_updates).
    cursor_updates: [{blockchain, factory_address, last_scanned_block}, ...]

    Incremental: start at last_scanned_block+1 when cursor exists (unless force_full_rescan).
    Missing RPC → skip that factory (warning), do not raise.
    """
    cfg = load_factories_config(factories_path)
    topics = [str(t).lower() for t in (cfg.get("create_topics") or [])]
    factories = cfg.get("factories") or []
    cursor_map = cursors or {}
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    cursor_updates: list[dict[str, Any]] = []

    if not topics:
        warnings.append("factories.yaml missing create_topics")
        return rows, warnings, cursor_updates

    for factory in factories:
        if not isinstance(factory, dict):
            continue
        blockchain = str(factory.get("blockchain") or "").strip().lower()
        factory_addr = _norm_addr(factory.get("address"))
        if not factory_addr or not blockchain:
            continue
        rpc_url = resolve_rpc_url(blockchain, rpc_overrides)
        if not rpc_url:
            warnings.append(
                f"skip factory {blockchain}/{factory_addr[:10]}…: "
                "missing ALCHEMY_KEY (or chain RPC override)"
            )
            continue
        try:
            latest = eth_block_number(rpc_url)
            yaml_from = int(factory.get("from_block") or 0)
            key = _cursor_key(blockchain, factory_addr)
            prev = int(cursor_map.get(key) or 0)
            if force_full_rescan:
                start = yaml_from
            elif prev > 0:
                start = max(yaml_from, prev + 1)
            else:
                # First touch: cheap lookback (Alchemy Free can't backfill millions of blocks).
                bootstrap = _bootstrap_blocks()
                start = max(yaml_from, latest - bootstrap) if bootstrap > 0 else yaml_from
            if max_blocks_per_factory is not None and max_blocks_per_factory > 0:
                start = max(start, latest - max_blocks_per_factory)

            if start > latest:
                cursor_updates.append(
                    {
                        "blockchain": blockchain,
                        "factory_address": factory_addr,
                        "last_scanned_block": latest,
                    }
                )
                continue

            all_logs = fetch_logs_adaptive(
                rpc_url,
                address=factory_addr,
                topics=topics,
                from_block=start,
                to_block=latest,
            )
            clones = parse_factory_clones_from_logs(all_logs, factory=factory)
            rows.extend(clones)
            cursor_updates.append(
                {
                    "blockchain": blockchain,
                    "factory_address": factory_addr,
                    "last_scanned_block": latest,
                }
            )
            print(
                f"  factory {blockchain}/{factory_addr[:10]}… "
                f"blocks {start}-{latest} logs={len(all_logs)} new_clones={len(clones)}",
                flush=True,
            )
        except (HTTPError, URLError, RuntimeError, TimeoutError, ValueError, OSError) as exc:
            warnings.append(f"factory_partial_failure {blockchain}/{factory_addr[:10]}…: {exc}")

    return rows, warnings, cursor_updates
