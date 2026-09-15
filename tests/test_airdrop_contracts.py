"""Tests for airdrop_contracts worker."""

from __future__ import annotations

from pathlib import Path

from workers.airdrop_contracts.merge import merge_rows
from workers.airdrop_contracts.parse_curated import load_curated_contracts
from workers.airdrop_contracts.parse_envio import (
    CHAIN_ID_TO_SLUG,
    campaign_to_row,
    collect_envio_clones,
)
from workers.airdrop_contracts.parse_spellbook import enrich_rows_with_spellbook, parse_claim_sql
from workers.airdrop_contracts.validate_onchain import has_bytecode, validate_rows

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


def test_campaign_to_row_maps_chain_and_asset():
    factory_meta = {
        "0x71dd3ca88e7564416e5c2e350090c12bf8f6144a": {
            "blockchain": "ethereum",
            "project_slug": "sablier",
            "project_name": "Sablier Airdrops",
        }
    }
    row = campaign_to_row(
        {
            "id": "0xaaa-1",
            "address": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "chainId": "1",
            "timestamp": "1738709075",
            "factory": {"address": "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a"},
            "asset": {
                "symbol": "UNI",
                "address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            },
        },
        factory_meta=factory_meta,
    )
    assert row is not None
    assert row["blockchain"] == "ethereum"
    assert row["address"] == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert row["source"] == "factory_clone"
    assert row["token_symbol"] == "UNI"
    assert row["raw"]["envio"]["chain_id"] == "1"
    assert CHAIN_ID_TO_SLUG["43114"] == "avalanche_c"


def test_campaign_to_row_drops_chain_mismatch():
    factory_meta = {
        "0x71dd3ca88e7564416e5c2e350090c12bf8f6144a": {
            "blockchain": "ethereum",
            "project_slug": "sablier",
            "project_name": "Sablier Airdrops",
        }
    }
    row = campaign_to_row(
        {
            "id": "0xbbb-10",
            "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "chainId": "10",
            "factory": {"address": "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a"},
            "asset": {},
        },
        factory_meta=factory_meta,
    )
    assert row is None


def test_collect_envio_clones_mocked(monkeypatch):
    from workers.airdrop_contracts import parse_envio as pe

    monkeypatch.setattr(
        pe,
        "fetch_campaigns_for_factories",
        lambda addrs, endpoint=None, page_size=None: [
            {
                "id": "0xccc-1",
                "address": "0xcccccccccccccccccccccccccccccccccccccccc",
                "chainId": "1",
                "timestamp": "1",
                "factory": {"address": "0x71DD3Ca88E7564416E5C2E350090C12Bf8F6144a"},
                "asset": {"symbol": "X", "address": "0x1111111111111111111111111111111111111111"},
            }
        ],
    )
    rows, warnings = collect_envio_clones(factories_path=PKG / "factories.yaml")
    assert not any("envio_fetch_failed" in w for w in warnings)
    assert len(rows) == 1
    assert rows[0]["blockchain"] == "ethereum"


def test_validate_trusts_envio_factory_clone_without_rpc(monkeypatch):
    monkeypatch.delenv("ALCHEMY_KEY", raising=False)
    rows = [
        {
            "blockchain": "ethereum",
            "address": "0xcccccccccccccccccccccccccccccccccccccccc",
            "project_slug": "sablier",
            "project_name": "Sablier",
            "source": "factory_clone",
            "token_address": None,
            "token_symbol": None,
            "factory_address": "0x71dd3ca88e7564416e5c2e350090c12bf8f6144a",
            "notes": None,
            "raw": {"envio": {"id": "0xccc-1", "chain_id": "1"}},
        }
    ]
    accepted, rejected = validate_rows(rows)
    assert len(accepted) == 1
    assert rejected == []


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
