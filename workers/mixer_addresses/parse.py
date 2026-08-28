"""Parse Tornado Cash docs and L2BEAT Privacy discovery into mixer row dicts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVM_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}")

TORNADO_DOCS_URL = (
    "https://raw.githubusercontent.com/tornadocash/docs/en/general/"
    "tornado-cash-smart-contracts.md"
)
TORNADO_DOCS_REPO = "tornadocash/docs"
TORNADO_DOCS_PATH = "general/tornado-cash-smart-contracts.md"

L2BEAT_RAW_BASE = (
    "https://raw.githubusercontent.com/l2beat/l2beat/main/packages/config/src/projects"
)

L2BEAT_PROJECT_SLUGS = (
    "cloaked",
    "privacy-pools",
    "railgun",
    "strk20",
    "tornado-cash",
    "umbra",
    "privacy-boost",
    "zama-cw",
)

L2BEAT_CHAIN_MAP: dict[str, str] = {
    "eth": "ethereum",
    "oeth": "optimism",
    "arb1": "arbitrum",
    "arbitrum": "arbitrum",
    "base": "base",
    "bsc": "bsc",
    "polygon": "polygon",
    "pol": "polygon",
    "gnosis": "gnosis",
    "xdai": "gnosis",
    "avax": "avalanche",
    "starknet": "starknet",
}

# Markdown section header -> blockchain slug (Tornado docs)
TORNADO_NETWORK_MAP: dict[str, str] = {
    "ethereum mainnet": "ethereum",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "bsc": "bsc",
    "xdai": "gnosis",
    "matic": "polygon",
    "avax": "avalanche",
}

STRK20_POOL_ADDRESS = (
    "0x040337b1af3c663e86e333bab5a4b28da8d4652a15a69beee2b677776ffe812a"
)

PROTOCOL_DISPLAY: dict[str, str] = {
    "tornado-cash": "Tornado Cash",
    "privacy-pools": "Privacy Pools",
    "railgun": "Railgun",
    "privacy-boost": "Privacy Boost",
    "umbra": "Umbra Cash",
    "cloaked": "Cloaked",
    "strk20": "STRK-20",
    "zama-cw": "Zama Confidential",
}


def normalize_evm_address(address: str) -> str:
    addr = address.strip()
    if addr.lower().startswith("0x") and len(addr) == 42:
        return "0x" + addr[2:].lower()
    return addr


def normalize_address(blockchain: str, address: str) -> str:
    if blockchain != "starknet" and address.lower().startswith("0x"):
        if len(address) == 42:
            return normalize_evm_address(address)
    return address.strip()


def parse_l2beat_address(raw: str) -> tuple[str, str] | None:
    raw = raw.strip()
    if ":" not in raw:
        return None
    chain_key, addr = raw.split(":", 1)
    chain_key = chain_key.strip().lower()
    blockchain = L2BEAT_CHAIN_MAP.get(chain_key)
    if not blockchain:
        return None
    addr = addr.strip()
    if not addr:
        return None
    return blockchain, normalize_address(blockchain, addr)


def _infer_role(name: str, template: str) -> str | None:
    combined = f"{name} {template}".lower()
    if name == "RailgunSmartWallet":
        return "pool"
    if "entrypoint" in combined or name == "Umbra":
        return "entrypoint"
    if name == "ConfidentialTokenWrappersRegistry":
        return "entrypoint"
    if "router" in combined or "relayadapt" in combined:
        return "router"
    if "pool" in combined or "tornado" in template.lower() or "privacyboost" in combined:
        return "pool"
    if "wrapper" in template.lower() and "confidential" in template.lower():
        return "pool"
    if name.startswith("Confidential") and name.endswith("Wrapper"):
        return "pool"
    return None


def _tornado_pool_template(template: str) -> bool:
    t = template.lower()
    return (
        "tornadocash_eth" in t
        or "tornadocash_erc20" in t
        or "erc20tornado" in t
        or "ctornado" in t
        or template.startswith("tornado-cash/TornadoCash")
    )


def _tornado_router(name: str, template: str) -> bool:
    return name == "TornadoRouter" or "tornadorouter" in template.lower()


def l2beat_entry_allowed(protocol: str, name: str, template: str) -> bool:
    if protocol == "tornado-cash":
        return _tornado_pool_template(template) or _tornado_router(name, template)
    if protocol == "privacy-pools":
        return name.startswith("PrivacyPool") or name == "PrivacyPoolsEntrypoint"
    if protocol == "railgun":
        return name in ("RailgunSmartWallet", "RelayAdapt")
    if protocol == "privacy-boost":
        return name == "PrivacyBoost"
    if protocol == "umbra":
        return name == "Umbra"
    if protocol == "cloaked":
        return False
    if protocol == "strk20":
        return False
    if protocol == "zama-cw":
        return (
            name == "ConfidentialTokenWrappersRegistry"
            or (name.startswith("Confidential") and name.endswith("Wrapper"))
        )
    return False


def _parse_asset_from_label(label: str) -> tuple[str | None, str | None]:
    label = label.strip()
    if not label or label.lower() == "contract":
        return None, label or None
    parts = label.split()
    if len(parts) >= 2 and parts[-1].isalpha() or parts[-1] in ("ETH", "DAI", "USDC", "USDT", "WBTC", "BNB", "MATIC", "AVAX", "xDAI"):
        asset = parts[-1].upper().replace("XDAI", "xDAI")
        return asset, label
    if parts and parts[0].replace(".", "").replace(",", "").isdigit():
        return None, label
    return None, label


def collect_tornado_docs_rows(markdown: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    in_classic_pools = False
    in_nova = False
    in_relayer = False
    current_chain: str | None = None

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("### tornado cash classic"):
            in_classic_pools = True
            in_nova = False
            in_relayer = False
            current_chain = None
            continue
        if lower.startswith("### tornado cash nova"):
            in_classic_pools = False
            in_nova = True
            in_relayer = False
            current_chain = "gnosis"
            continue
        if lower.startswith("### relayer registry"):
            in_classic_pools = False
            in_nova = False
            in_relayer = True
            current_chain = "ethereum"
            continue
        if lower.startswith("### governance") or lower.startswith("### other contracts"):
            in_classic_pools = False
            in_nova = False
            in_relayer = False
            continue

        if in_classic_pools and stripped.startswith("* ") and not stripped.startswith("* ["):
            net = stripped.lstrip("* ").strip().lower()
            if net == "goerli":
                current_chain = None
                continue
            current_chain = TORNADO_NETWORK_MAP.get(net)
            continue

        if not (in_classic_pools or in_nova or in_relayer):
            continue
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        if "contract" in lower and "address" in lower:
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, addr_cell = cells[0], cells[1]

        if in_relayer:
            if "tornado router" not in label.lower():
                continue
        elif in_nova:
            if label.lower() == "contract":
                pass
            elif "omnibridge" in label.lower() or "verifier" in label.lower() or "hasher" in label.lower():
                continue

        addrs = EVM_ADDRESS.findall(addr_cell)
        if not addrs:
            continue
        addr = normalize_evm_address(addrs[0])
        if current_chain is None:
            continue

        if in_relayer:
            role = "router"
        else:
            role = "pool"

        asset, denomination = _parse_asset_from_label(label)
        rows.append(
            {
                "blockchain": current_chain,
                "address": addr,
                "protocol": "tornado-cash",
                "protocol_name": "Tornado Cash",
                "contract_name": label,
                "contract_role": role,
                "asset_symbol": asset,
                "denomination": denomination,
                "source": "tornado-docs",
            }
        )

    return rows


def collect_l2beat_rows_from_discovery(
    protocol: str,
    discovery: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    protocol_name = PROTOCOL_DISPLAY.get(protocol, protocol)

    if protocol == "strk20":
        rows.append(
            {
                "blockchain": "starknet",
                "address": STRK20_POOL_ADDRESS,
                "protocol": protocol,
                "protocol_name": protocol_name,
                "contract_name": "STRK20Pool",
                "contract_role": "pool",
                "asset_symbol": None,
                "denomination": None,
                "source": "l2beat",
            }
        )
        return rows

    for entry in discovery.get("entries", []):
        if entry.get("type") != "Contract":
            continue
        name = str(entry.get("name") or "")
        template = str(entry.get("template") or "")
        if not l2beat_entry_allowed(protocol, name, template):
            continue
        parsed = parse_l2beat_address(str(entry.get("address") or ""))
        if not parsed:
            continue
        blockchain, address = parsed
        role = _infer_role(name, template)
        if role is None:
            continue
        rows.append(
            {
                "blockchain": blockchain,
                "address": address,
                "protocol": protocol,
                "protocol_name": protocol_name,
                "contract_name": name,
                "contract_role": role,
                "asset_symbol": None,
                "denomination": None,
                "source": "l2beat",
            }
        )

    return rows


def merge_mixer_rows(
    tornado_rows: list[dict[str, Any]],
    l2beat_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Dedup by (blockchain, address); L2BEAT wins over tornado-docs."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in tornado_rows:
        key = (row["blockchain"], row["address"])
        by_key[key] = row
    for row in l2beat_rows:
        key = (row["blockchain"], row["address"])
        by_key[key] = row
    return sorted(by_key.values(), key=lambda r: (r["blockchain"], r["address"]))


def collect_mixer_rows(
    *,
    tornado_markdown: str,
    l2beat_discoveries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    tornado_rows = collect_tornado_docs_rows(tornado_markdown)
    l2beat_rows: list[dict[str, Any]] = []
    for slug, discovery in l2beat_discoveries.items():
        l2beat_rows.extend(collect_l2beat_rows_from_discovery(slug, discovery))
    return merge_mixer_rows(tornado_rows, l2beat_rows)


def load_l2beat_discovery(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_l2beat_rows_from_dir(projects_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slug in L2BEAT_PROJECT_SLUGS:
        if slug == "strk20":
            rows.extend(collect_l2beat_rows_from_discovery(slug, {}))
            continue
        path = projects_dir / slug / "discovered.json"
        if not path.is_file():
            continue
        rows.extend(
            collect_l2beat_rows_from_discovery(slug, load_l2beat_discovery(path))
        )
    return rows
