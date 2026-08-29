"""Tests for airdrop_contracts worker."""

from __future__ import annotations

from pathlib import Path

from workers.airdrop_contracts.merge import merge_rows
from workers.airdrop_contracts.parse_curated import load_curated_contracts
from workers.airdrop_contracts.parse_factories import parse_factory_clones_from_logs
from workers.airdrop_contracts.parse_spellbook import enrich_rows_with_spellbook, parse_claim_sql
from workers.airdrop_contracts.validate_onchain import has_bytecode

PKG = Path(__file__).resolve().parents[1] / "workers" / "airdrop_contracts"


def test_load_curated_min_rows():
    rows = load_curated_contracts(PKG / "contracts.yaml")
    assert len(rows) >= 10
    assert all(r["source"] == "walpulse_curated" for r in rows)
    assert all(r["address"].startswith("0x") and len(r["address"]) == 42 for r in rows)


def test_merge_curated_wins():
    curated = [
        {
            "blockchain": "ethereum",
            "address": "0xabc0000000000000000000000000000000000001",
            "project_slug": "uni",
            "project_name": "Uniswap",
            "source": "walpulse_curated",
            "token_address": "0x1111111111111111111111111111111111111111",
            "token_symbol": "UNI",
            "factory_address": None,
            "notes": None,
            "raw": {},
        }
    ]
    clone = [
        {
            "blockchain": "ethereum",
            "address": "0xabc0000000000000000000000000000000000001",
            "project_slug": "sablier",
            "project_name": "Sablier",
            "source": "factory_clone",
            "token_address": None,
            "token_symbol": None,
            "factory_address": "0xdef0000000000000000000000000000000000002",
            "notes": None,
            "raw": {},
        }
    ]
    merged = merge_rows(curated, clone)
    assert len(merged) == 1
    assert merged[0]["source"] == "walpulse_curated"
    assert merged[0]["token_symbol"] == "UNI"


def test_parse_factory_logs_extracts_campaign():
    factory = {
        "blockchain": "ethereum",
        "address": "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a",
        "project_slug": "sablier",
        "project_name": "Sablier Airdrops",
        "family": "sablier",
        "version": "v1.3.0",
    }
    logs = [
        {
            "topics": [
                "0xca58fb398f60b2cc5e664a08608a6aabe7077d2684a2d82a7d5b83322fd2b2a7",
                "0x000000000000000000000000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            ],
            "transactionHash": "0xdead",
            "blockNumber": "0x1",
        }
    ]
    rows = parse_factory_clones_from_logs(logs, factory=factory)
    assert len(rows) == 1
    assert rows[0]["address"] == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert rows[0]["source"] == "factory_clone"
    assert rows[0]["factory_address"] == "0x71dd3ca88e7564416e5c2e350090c12bf8f6144a"


def test_parse_spellbook_claim_sql():
    text = """
    {% set token_address = '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984' %}
    select * from {{ source('uniswap', 'MerkleDistributor_evt_Claimed') }}
    """
    meta = parse_claim_sql(
        Path("models/_sector/airdrops/ethereum/projects/uniswap/uniswap_ethereum_airdrop_claims.sql"),
        text,
    )
    assert meta is not None
    assert meta["project_slug"] == "uniswap"
    assert meta["blockchain"] == "ethereum"
    assert meta["token_address"].startswith("0x1f98")
    assert meta["event_table"] == "MerkleDistributor_evt_Claimed"


def test_enrich_spellbook():
    rows = [
        {
            "blockchain": "ethereum",
            "address": "0x090d4613473dee047c3f2706764f49e0821d256e",
            "project_slug": "uniswap",
            "project_name": "Uniswap",
            "source": "walpulse_curated",
            "token_address": None,
            "token_symbol": "UNI",
            "factory_address": None,
            "notes": None,
            "raw": {},
        }
    ]
    meta = {
        "uniswap": {
            "blockchain": "ethereum",
            "project_slug": "uniswap",
            "token_address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            "event_source": "uniswap",
            "event_table": "MerkleDistributor_evt_Claimed",
            "spellbook_path": "x.sql",
        }
    }
    out = enrich_rows_with_spellbook(rows, meta)
    assert out[0]["token_address"].startswith("0x1f98")
    assert out[0]["raw"]["spellbook"]["event_table"] == "MerkleDistributor_evt_Claimed"


def test_has_bytecode():
    assert has_bytecode("0x60806040")
    assert not has_bytecode("0x")
    assert not has_bytecode("0x0")


def test_alchemy_rpc_url():
    from workers.airdrop_contracts.rpc import alchemy_rpc_url, resolve_rpc_url

    url = alchemy_rpc_url("ethereum", "testkey")
    assert url == "https://eth-mainnet.g.alchemy.com/v2/testkey"
    assert alchemy_rpc_url("nope", "testkey") is None

    import os

    os.environ["ALCHEMY_KEY"] = "abc"
    for k in ("ETH_RPC_URL",):
        os.environ.pop(k, None)
    assert resolve_rpc_url("base").endswith("/v2/abc")
    os.environ["ETH_RPC_URL"] = "https://custom.example/eth"
    assert resolve_rpc_url("ethereum") == "https://custom.example/eth"
    os.environ.pop("ETH_RPC_URL", None)
    os.environ.pop("ALCHEMY_KEY", None)


def test_incremental_start_uses_cursor(monkeypatch):
    """With a cursor, collect should start after last_scanned_block (no full history)."""
    from workers.airdrop_contracts import parse_factories as pf

    calls: list[tuple[int, int]] = []

    def fake_logs(rpc_url, *, address, topics, from_block, to_block):
        calls.append((from_block, to_block))
        return []

    monkeypatch.setattr(pf, "eth_block_number", lambda _u: 100_000)
    monkeypatch.setattr(pf, "eth_get_logs", fake_logs)
    monkeypatch.setattr(
        pf,
        "resolve_rpc_url",
        lambda chain, overrides=None: "https://example.invalid",
    )
    monkeypatch.setattr(
        pf,
        "load_factories_config",
        lambda path=None: {
            "create_topics": ["0xca58fb398f60b2cc5e664a08608a6aabe7077d2684a2d82a7d5b83322fd2b2a7"],
            "factories": [
                {
                    "family": "sablier",
                    "version": "v1.3.0",
                    "blockchain": "ethereum",
                    "address": "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a",
                    "from_block": 1,
                    "project_slug": "sablier",
                    "project_name": "Sablier",
                }
            ],
        },
    )
    key = pf._cursor_key("ethereum", "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a")
    rows, warnings, cursors = pf.collect_factory_clones(
        cursors={key: 90_000},
        force_full_rescan=False,
    )
    assert not warnings
    assert rows == []
    assert calls
    assert calls[0][0] == 90_001
    assert cursors[0]["last_scanned_block"] == 100_000
