"""Resolve JSON-RPC URLs from ALCHEMY_KEY (or per-chain env overrides)."""

from __future__ import annotations

import os

# Alchemy subdomain per Walpulse blockchain slug.
ALCHEMY_NETWORK: dict[str, str] = {
    "ethereum": "eth-mainnet",
    "optimism": "opt-mainnet",
    "arbitrum": "arb-mainnet",
    "base": "base-mainnet",
    "polygon": "polygon-mainnet",
    "bnb": "bnb-mainnet",
    "gnosis": "gnosis-mainnet",
    "avalanche_c": "avax-mainnet",
    "scroll": "scroll-mainnet",
    "linea": "linea-mainnet",
    "zksync": "zksync-mainnet",
}

# Optional explicit env overrides (take precedence over ALCHEMY_KEY).
RPC_ENV_OVERRIDE: dict[str, str] = {
    "ethereum": "ETH_RPC_URL",
    "optimism": "OPTIMISM_RPC_URL",
    "arbitrum": "ARBITRUM_RPC_URL",
    "base": "BASE_RPC_URL",
    "polygon": "POLYGON_RPC_URL",
    "bnb": "BNB_RPC_URL",
    "gnosis": "GNOSIS_RPC_URL",
    "avalanche_c": "AVALANCHE_RPC_URL",
    "scroll": "SCROLL_RPC_URL",
    "linea": "LINEA_RPC_URL",
    "zksync": "ZKSYNC_RPC_URL",
}


def alchemy_rpc_url(blockchain: str, api_key: str) -> str | None:
    network = ALCHEMY_NETWORK.get(blockchain.strip().lower())
    key = (api_key or "").strip()
    if not network or not key:
        return None
    return f"https://{network}.g.alchemy.com/v2/{key}"


def resolve_rpc_url(blockchain: str, overrides: dict[str, str] | None = None) -> str:
    """
    Precedence:
    1. overrides[blockchain]
    2. per-chain env (ETH_RPC_URL, …)
    3. ALCHEMY_KEY → Alchemy URL for that chain
    """
    chain = blockchain.strip().lower()
    if overrides and chain in overrides and overrides[chain].strip():
        return overrides[chain].strip()
    env_name = RPC_ENV_OVERRIDE.get(chain)
    if env_name:
        explicit = (os.environ.get(env_name) or "").strip()
        if explicit:
            return explicit
    alchemy = alchemy_rpc_url(chain, os.environ.get("ALCHEMY_KEY") or "")
    return alchemy or ""
