"""Parse bridge gateway contract addresses from multiple open sources."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVM_ADDRESS = re.compile(r"0x[a-fA-F0-9]{40}")
NULL_EVM = "0x0000000000000000000000000000000000000000"

DEFILLAMA_REPO = "DefiLlama/bridges-server"
DEFILLAMA_DATA_PATH = "src/data/bridgeNetworkData.ts"

STARGATE_API_URL = "https://mainnet.stargate-api.com/v1/metadata?version=v2"
WORMHOLE_CONSTS_URL = (
    "https://raw.githubusercontent.com/wormhole-foundation/wormhole/main/"
    "sdk/js/src/utils/consts.ts"
)
HOP_ADAPTER_URL = (
    "https://raw.githubusercontent.com/DefiLlama/bridges-server/master/"
    "src/adapters/hop/index.ts"
)
CCIP_CHAINS_URL = "https://docs.chain.link/api/ccip/v1/chains?environment=mainnet"
ACROSS_ADDRESSES_URL = (
    "https://raw.githubusercontent.com/across-protocol/contracts/master/"
    "broadcast/deployed-addresses.json"
)
AXELAR_CONFIG_URL = (
    "https://axelar-mainnet.s3.us-east-2.amazonaws.com/configs/mainnet-config-1.x.json"
)

SOURCE_PRIORITY: dict[str, int] = {
    "across-docs": 0,
    "ccip-docs": 0,
    "stargate-api": 1,
    "wormhole-consts": 1,
    "hop-addresses": 1,
    "axelar-config": 1,
    "defillama": 2,
}

DEFILLAMA_CHAIN_MAP: dict[str, str] = {
    "ethereum": "ethereum",
    "polygon": "polygon",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "bsc": "bsc",
    "binance": "bsc",
    "avax": "avalanche",
    "avalanche": "avalanche",
    "xdai": "gnosis",
    "gnosis": "gnosis",
    "base": "base",
    "fantom": "fantom",
    "aurora": "aurora",
    "celo": "celo",
    "moonbeam": "moonbeam",
    "moonriver": "moonriver",
    "metis": "metis",
    "linea": "linea",
    "scroll": "scroll",
    "mantle": "mantle",
    "blast": "blast",
    "zksync era": "zksync",
    "zksync": "zksync",
    "era": "zksync",
    "polygon zkevm": "polygon_zkevm",
    "arbitrum nova": "arbitrum_nova",
    "solana": "solana",
    "aptos": "aptos",
    "sui": "sui",
    "tron": "tron",
    "near": "near",
    "starknet": "starknet",
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ronin": "ronin",
    "sei": "sei",
    "world chain": "worldchain",
    "wc": "worldchain",
    "unichain": "unichain",
    "ink": "ink",
    "berachain": "berachain",
    "bera": "berachain",
    "sonic": "sonic",
    "flare": "flare",
    "rootstock": "rsk",
    "rsk": "rootstock",
    "klaytn": "klaytn",
    "kaia": "klaytn",
    "hyperevm": "hyperliquid",
    "hyperliquid": "hyperliquid",
}

CCIP_INTERNAL_CHAIN_MAP: dict[str, str] = {
    "ethereum-mainnet": "ethereum",
    "ethereum-mainnet-arbitrum-1": "arbitrum",
    "ethereum-mainnet-optimism-1": "optimism",
    "ethereum-mainnet-base-1": "base",
    "ethereum-mainnet-linea-1": "linea",
    "ethereum-mainnet-scroll-1": "scroll",
    "ethereum-mainnet-zksync-1": "zksync",
    "ethereum-mainnet-mode-1": "mode",
    "ethereum-mainnet-metis-1": "metis",
    "ethereum-mainnet-mantle-1": "mantle",
    "ethereum-mainnet-zircuit-1": "zircuit",
    "ethereum-mainnet-taiko-1": "taiko",
    "ethereum-mainnet-ink-1": "ink",
    "ethereum-mainnet-unichain-1": "unichain",
    "ethereum-mainnet-worldchain-1": "worldchain",
    "polygon-mainnet": "polygon",
    "binance_smart_chain-mainnet": "bsc",
    "avalanche-mainnet": "avalanche",
    "solana-mainnet": "solana",
    "aptos-mainnet": "aptos",
    "gnosis_chain-mainnet": "gnosis",
    "celo-mainnet": "celo",
    "ronin-mainnet": "ronin",
    "sei-mainnet": "sei",
    "berachain-mainnet": "berachain",
    "sonic-mainnet": "sonic",
    "plasma-mainnet": "plasma",
    "monad-mainnet": "monad",
    "tempo-mainnet": "tempo",
    "robinhood-mainnet": "robinhood",
    "rootstock-mainnet": "rootstock",
    "kaia-mainnet": "klaytn",
    "hyperliquid-mainnet": "hyperliquid",
    "flare-mainnet": "flare",
    "soneium-mainnet": "soneium",
}

ACROSS_CHAIN_ID_MAP: dict[str, str] = {
    "1": "ethereum",
    "10": "optimism",
    "56": "bsc",
    "130": "unichain",
    "137": "polygon",
    "232": "lens",
    "324": "zksync",
    "480": "worldchain",
    "999": "hyperliquid",
    "8453": "base",
    "42161": "arbitrum",
    "57073": "ink",
    "59144": "linea",
    "81457": "blast",
    "9745": "plasma",
    "534352": "scroll",
    "1868": "soneium",
    "4217": "tempo",
    "4663": "robinhood",
    "728126428": "tron",
    "34268394551451": "solana",
    "143": "monad",
    "4326": "megaeth",
}

ACROSS_CONTRACT_ROLES: dict[str, str] = {
    "SpokePool": "spoke_pool",
    "HubPool": "hub_pool",
}

AXELAR_CHAIN_MAP: dict[str, str] = {
    "ethereum": "ethereum",
    "polygon": "polygon",
    "avalanche": "avalanche",
    "fantom": "fantom",
    "moonbeam": "moonbeam",
    "binance": "bsc",
    "bsc": "bsc",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "base": "base",
    "linea": "linea",
    "scroll": "scroll",
    "celo": "celo",
    "kava": "kava",
    "filecoin": "filecoin",
    "mantle": "mantle",
    "blast": "blast",
    "fraxtal": "fraxtal",
}

EXCLUDED_ADDRESS_KEYS = frozenset(
    {"nativeToken", "native", "weth", "weth9", "token", "tokens", "ercs", "lpToken"}
)
EXCLUDED_CHAIN_KEYS = frozenset(
    {"token", "tokens", "tokenaddresses", "nativetoken", "native", "ercs", "lptoken"}
)
EXCLUDED_ARRAY_KEYS = frozenset({"EOAs", "eoa", "EOA"})


def normalize_chain(raw: str) -> str | None:
    key = raw.strip().lower().replace("-", " ").replace("_", " ")
    key = " ".join(key.split())
    mapped = DEFILLAMA_CHAIN_MAP.get(key)
    if mapped:
        return mapped
    slug = key.replace(" ", "_")
    return slug or None


def normalize_evm_address(address: str) -> str:
    addr = address.strip()
    if addr.lower().startswith("0x") and len(addr) == 42:
        return "0x" + addr[2:].lower()
    return addr


def normalize_address(blockchain: str, address: str) -> str:
    addr = address.strip()
    if addr.lower().startswith("0x") and len(addr) == 42:
        return normalize_evm_address(addr)
    return addr


def _row(
    *,
    blockchain: str,
    address: str,
    bridge_slug: str,
    bridge_name: str,
    contract_name: str,
    contract_role: str,
    source: str,
    asset_symbol: str | None = None,
) -> dict[str, Any]:
    chain = normalize_chain(blockchain) or blockchain
    return {
        "blockchain": chain,
        "address": normalize_address(chain, address),
        "bridge_slug": bridge_slug,
        "bridge_name": bridge_name,
        "contract_name": contract_name,
        "contract_role": contract_role,
        "asset_symbol": asset_symbol,
        "source": source,
    }


def _is_null_evm(address: str) -> bool:
    return address.lower() == NULL_EVM


def _parse_bridge_network_metadata(text: str) -> dict[str, str]:
    names: dict[str, str] = {}
    blocks = re.split(r"\n\s*\{", text)
    for block in blocks:
        db_match = re.search(r'bridgeDbName:\s*"([^"]+)"', block)
        name_match = re.search(r'displayName:\s*"([^"]+)"', block)
        if db_match and name_match:
            names[db_match.group(1)] = name_match.group(1)
    return names


def _extract_const_object(text: str, var_name: str) -> str | None:
    pattern = rf"const\s+{re.escape(var_name)}\s*=\s*\{{"
    match = re.search(pattern, text)
    if not match:
        return None
    start = match.end() - 1
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


def _parse_nested_address_map(
    block: str,
    *,
    bridge_slug: str,
    bridge_name: str,
    source: str,
    default_role: str = "gateway",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    chain_pattern = re.compile(r"([a-zA-Z0-9_ \"-]+):\s*\{", re.MULTILINE)
    for chain_match in chain_pattern.finditer(block):
        chain_raw = chain_match.group(1).strip().strip('"')
        chain_key = chain_raw.lower().replace(" ", "").replace("_", "")
        if chain_key in EXCLUDED_CHAIN_KEYS:
            continue
        chain = normalize_chain(chain_raw)
        if not chain or chain.lower() in EXCLUDED_CHAIN_KEYS:
            continue
        sub_start = chain_match.end() - 1
        depth = 0
        sub_end = sub_start
        for i in range(sub_start, len(block)):
            if block[i] == "{":
                depth += 1
            elif block[i] == "}":
                depth -= 1
                if depth == 0:
                    sub_end = i + 1
                    break
        sub = block[sub_start:sub_end]
        for key_match in re.finditer(r"([A-Za-z0-9_]+):\s*\"(0x[a-fA-F0-9]{40})\"", sub):
            key = key_match.group(1)
            if key in EXCLUDED_ADDRESS_KEYS:
                continue
            addr = key_match.group(2)
            if _is_null_evm(addr):
                continue
            role = default_role
            if key.lower() in {"router", "routers", "stg"}:
                role = "router"
            elif key.lower() == "factory":
                role = "factory"
            elif key.lower() == "ethervault":
                role = "vault"
            rows.append(
                _row(
                    blockchain=chain,
                    address=addr,
                    bridge_slug=bridge_slug,
                    bridge_name=bridge_name,
                    contract_name=f"{chain}:{key}",
                    contract_role=role,
                    source=source,
                    asset_symbol=key if key.isupper() and len(key) <= 8 else None,
                )
            )
        for arr_match in re.finditer(
            r"([A-Za-z0-9_]+):\s*\[(.*?)\]", sub, flags=re.DOTALL
        ):
            arr_key = arr_match.group(1)
            if arr_key in EXCLUDED_ARRAY_KEYS:
                continue
            role = "router" if "router" in arr_key.lower() else "gateway"
            for addr in EVM_ADDRESS.findall(arr_match.group(2)):
                if _is_null_evm(addr):
                    continue
                rows.append(
                    _row(
                        blockchain=chain,
                        address=addr,
                        bridge_slug=bridge_slug,
                        bridge_name=bridge_name,
                        contract_name=f"{chain}:{arr_key}",
                        contract_role=role,
                        source=source,
                    )
                )
    return rows


def collect_defillama_rows(adapters_dir: Path, network_data_text: str) -> list[dict[str, Any]]:
    display_names = _parse_bridge_network_metadata(network_data_text)
    rows: list[dict[str, Any]] = []
    if not adapters_dir.is_dir():
        return rows

    for adapter_path in sorted(adapters_dir.glob("*/index.ts")):
        slug = adapter_path.parent.name
        text = adapter_path.read_text(encoding="utf-8")
        bridge_name = display_names.get(slug, slug.replace("-", " ").title())

        contract_block = _extract_const_object(text, "contractAddresses")
        if contract_block:
            rows.extend(
                _parse_nested_address_map(
                    contract_block,
                    bridge_slug=slug,
                    bridge_name=bridge_name,
                    source="defillama",
                )
            )

        for target_match in re.finditer(r'target:\s*"(0x[a-fA-F0-9]{40})"', text):
            addr = target_match.group(1)
            if _is_null_evm(addr):
                continue
            rows.append(
                _row(
                    blockchain="ethereum",
                    address=addr,
                    bridge_slug=slug,
                    bridge_name=bridge_name,
                    contract_name="event_target",
                    contract_role="gateway",
                    source="defillama",
                )
            )

        for arr_match in re.finditer(
            r"(routers|gateways|bridgeContracts)\s*[:=]\s*\[(.*?)\]",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            arr_key = arr_match.group(1)
            for addr in EVM_ADDRESS.findall(arr_match.group(2)):
                if _is_null_evm(addr):
                    continue
                rows.append(
                    _row(
                        blockchain="ethereum",
                        address=addr,
                        bridge_slug=slug,
                        bridge_name=bridge_name,
                        contract_name=arr_key,
                        contract_role="router" if "router" in arr_key.lower() else "gateway",
                        source="defillama",
                    )
                )
    return rows


def collect_hop_rows(hop_adapter_text: str) -> list[dict[str, Any]]:
    block = _extract_const_object(hop_adapter_text, "contractAddresses")
    if not block:
        return []
    return _parse_nested_address_map(
        block,
        bridge_slug="hop",
        bridge_name="Hop",
        source="hop-addresses",
    )


def collect_stargate_lz_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    assets = data.get("v2") if isinstance(data, dict) else []
    for item in assets:
        chain = normalize_chain(str(item.get("chainKey") or item.get("chainName") or ""))
        if not chain:
            continue
        stype = str(item.get("stargateType") or "")
        token = item.get("token") or {}
        symbol = token.get("symbol")
        pool_addr = item.get("address")
        if pool_addr and isinstance(pool_addr, str) and pool_addr.startswith("0x"):
            if not _is_null_evm(pool_addr):
                rows.append(
                    _row(
                        blockchain=chain,
                        address=pool_addr,
                        bridge_slug="stargate",
                        bridge_name="Stargate",
                        contract_name=f"stargate_{stype.lower()}",
                        contract_role="pool" if stype == "POOL" else "router",
                        source="stargate-api",
                        asset_symbol=str(symbol) if symbol else None,
                    )
                )
        messaging = item.get("tokenMessaging")
        if messaging and isinstance(messaging, str) and messaging.startswith("0x"):
            if not _is_null_evm(messaging):
                rows.append(
                    _row(
                        blockchain=chain,
                        address=messaging,
                        bridge_slug="stargate",
                        bridge_name="Stargate",
                        contract_name="tokenMessaging",
                        contract_role="router",
                        source="stargate-api",
                    )
                )
    return rows


def collect_wormhole_rows(consts_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mainnet_match = re.search(r"const\s+MAINNET\s*=\s*\{", consts_text)
    if not mainnet_match:
        return rows
    start = mainnet_match.end() - 1
    depth = 0
    end = start
    for i in range(start, len(consts_text)):
        if consts_text[i] == "{":
            depth += 1
        elif consts_text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    mainnet_block = consts_text[start:end]
    chain_pattern = re.compile(
        r"\n\s*([a-zA-Z0-9_]+):\s*\{\s*"
        r"core:\s*(?:\"([^\"]+)\"|undefined),?\s*"
        r"token_bridge:\s*(?:\"([^\"]+)\"|undefined)",
        re.MULTILINE,
    )
    for match in chain_pattern.finditer(mainnet_block):
        chain = match.group(1)
        if chain in {"unset"}:
            continue
        blockchain = normalize_chain(chain) or chain
        core, token_bridge = match.group(2), match.group(3)
        if core and core != "undefined":
            rows.append(
                _row(
                    blockchain=blockchain,
                    address=core,
                    bridge_slug="wormhole",
                    bridge_name="Wormhole",
                    contract_name="core",
                    contract_role="core",
                    source="wormhole-consts",
                )
            )
        if token_bridge and token_bridge != "undefined":
            rows.append(
                _row(
                    blockchain=blockchain,
                    address=token_bridge,
                    bridge_slug="wormhole",
                    bridge_name="Wormhole",
                    contract_name="token_bridge",
                    contract_role="token_bridge",
                    source="wormhole-consts",
                )
            )
    return rows


def _ccip_blockchain(family: str, internal_id: str, chain_id: Any) -> str | None:
    if internal_id in CCIP_INTERNAL_CHAIN_MAP:
        return CCIP_INTERNAL_CHAIN_MAP[internal_id]
    if family == "solana":
        return "solana"
    if family == "aptos":
        return "aptos"
    if isinstance(chain_id, int):
        fallback = {1: "ethereum", 10: "optimism", 56: "bsc", 137: "polygon", 42161: "arbitrum", 8453: "base", 43114: "avalanche"}
        return fallback.get(chain_id)
    return None


def collect_ccip_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = payload.get("data") or {}
    for family, chains in data.items():
        if not isinstance(chains, dict):
            continue
        for _cid, info in chains.items():
            if not isinstance(info, dict):
                continue
            internal_id = str(info.get("internalId") or "")
            blockchain = _ccip_blockchain(family, internal_id, info.get("chainId"))
            if not blockchain:
                continue
            router = info.get("router")
            if router and isinstance(router, str) and router.strip():
                rows.append(
                    _row(
                        blockchain=blockchain,
                        address=router,
                        bridge_slug="ccip",
                        bridge_name="Chainlink CCIP",
                        contract_name="router",
                        contract_role="router",
                        source="ccip-docs",
                    )
                )
    return rows


def collect_across_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chain_id, chain_data in (payload.get("chains") or {}).items():
        blockchain = ACROSS_CHAIN_ID_MAP.get(str(chain_id))
        if not blockchain:
            continue
        for name, info in (chain_data.get("contracts") or {}).items():
            if not isinstance(info, dict):
                continue
            addr = info.get("address")
            if not addr or not isinstance(addr, str):
                continue
            if addr.startswith("0x") and _is_null_evm(addr):
                continue
            role = ACROSS_CONTRACT_ROLES.get(name)
            if role:
                contract_role = role
            elif name.endswith("_Adapter"):
                contract_role = "adapter"
            elif "Bridge" in name or "Bridger" in name:
                contract_role = "gateway"
            else:
                continue
            rows.append(
                _row(
                    blockchain=blockchain,
                    address=addr,
                    bridge_slug="across",
                    bridge_name="Across",
                    contract_name=name,
                    contract_role=contract_role,
                    source="across-docs",
                )
            )
    return rows


def collect_axelar_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chain_id, chain_cfg in (payload.get("chains") or {}).items():
        if not isinstance(chain_cfg, dict):
            continue
        if str(chain_cfg.get("chainType") or "") != "evm":
            continue
        blockchain = AXELAR_CHAIN_MAP.get(str(chain_id).lower()) or normalize_chain(str(chain_id))
        if not blockchain:
            continue
        contracts = (chain_cfg.get("config") or {}).get("contracts") or {}
        for name in ("AxelarGateway", "InterchainTokenService"):
            info = contracts.get(name)
            if not isinstance(info, dict):
                continue
            addr = info.get("address")
            if not addr:
                continue
            rows.append(
                _row(
                    blockchain=blockchain,
                    address=str(addr),
                    bridge_slug="axelar",
                    bridge_name="Axelar",
                    contract_name=name,
                    contract_role="gateway" if "Gateway" in name else "router",
                    source="axelar-config",
                )
            )
    return rows


def merge_bridge_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        for row in group:
            key = (row["blockchain"], row["address"])
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = row
                continue
            if SOURCE_PRIORITY.get(row["source"], 99) < SOURCE_PRIORITY.get(existing["source"], 99):
                by_key[key] = row
    return sorted(by_key.values(), key=lambda r: (r["blockchain"], r["address"]))


def collect_bridge_rows(
    *,
    defillama_adapters_dir: Path,
    bridge_network_data: str,
    stargate_payload: dict[str, Any],
    wormhole_consts: str,
    hop_adapter_text: str,
    ccip_payload: dict[str, Any],
    across_payload: dict[str, Any],
    axelar_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    return merge_bridge_rows(
        collect_defillama_rows(defillama_adapters_dir, bridge_network_data),
        collect_stargate_lz_rows(stargate_payload),
        collect_wormhole_rows(wormhole_consts),
        collect_hop_rows(hop_adapter_text),
        collect_ccip_rows(ccip_payload),
        collect_across_rows(across_payload),
        collect_axelar_rows(axelar_payload),
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
