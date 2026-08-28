"""Tests for workers.mixer_addresses.parse."""

from __future__ import annotations

import json
from pathlib import Path

from workers.mixer_addresses.parse import (
    collect_l2beat_rows_from_discovery,
    collect_mixer_rows,
    collect_tornado_docs_rows,
    merge_mixer_rows,
    normalize_evm_address,
    parse_l2beat_address,
    privacy_mechanism,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_evm_address_lowercase() -> None:
    assert (
        normalize_evm_address("0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936")
        == "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936"
    )


def test_parse_l2beat_address_eth() -> None:
    assert parse_l2beat_address("eth:0x6818809EefCe719E480a7526D76bD3e561526b46") == (
        "ethereum",
        "0x6818809eefce719e480a7526d76bd3e561526b46",
    )


def test_collect_tornado_docs_fixture() -> None:
    md = (FIXTURES / "tornado_docs_sample.md").read_text(encoding="utf-8")
    rows = collect_tornado_docs_rows(md)
    assert len(rows) == 4
    roles = {r["contract_role"] for r in rows}
    assert roles == {"pool", "router"}
    eth_pools = [r for r in rows if r["blockchain"] == "ethereum" and r["contract_role"] == "pool"]
    assert len(eth_pools) == 2
    assert eth_pools[0]["asset_symbol"] == "ETH"
    assert all(r["privacy_mechanism"] == "zk_pool" for r in rows)


def test_privacy_mechanism_by_protocol() -> None:
    assert privacy_mechanism("tornado-cash") == "zk_pool"
    assert privacy_mechanism("privacy-pools") == "zk_pool"
    assert privacy_mechanism("umbra") == "stealth"
    assert privacy_mechanism("zama-cw") == "fhe_wrapper"
    assert privacy_mechanism("privacy-boost") == "tee"


def test_collect_l2beat_privacy_pools_fixture() -> None:
    disc = json.loads((FIXTURES / "privacy_pools_discovery_sample.json").read_text())
    rows = collect_l2beat_rows_from_discovery("privacy-pools", disc)
    assert len(rows) == 2
    names = {r["contract_name"] for r in rows}
    assert names == {"PrivacyPoolUSDS", "PrivacyPoolsEntrypoint"}
    assert all(r["source"] == "l2beat" for r in rows)
    assert all(r["privacy_mechanism"] == "zk_pool" for r in rows)


def test_merge_prefers_l2beat_on_collision() -> None:
    tornado = [
        {
            "blockchain": "ethereum",
            "address": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
            "protocol": "tornado-cash",
            "protocol_name": "Tornado Cash",
            "contract_name": "1 ETH",
            "contract_role": "pool",
            "privacy_mechanism": "zk_pool",
            "asset_symbol": "ETH",
            "denomination": "1 ETH",
            "source": "tornado-docs",
        }
    ]
    l2beat = [
        {
            "blockchain": "ethereum",
            "address": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
            "protocol": "tornado-cash",
            "protocol_name": "Tornado Cash",
            "contract_name": "Pool_1_ETH",
            "contract_role": "pool",
            "privacy_mechanism": "zk_pool",
            "asset_symbol": None,
            "denomination": None,
            "source": "l2beat",
        }
    ]
    merged = merge_mixer_rows(tornado, l2beat)
    assert len(merged) == 1
    assert merged[0]["source"] == "l2beat"
    assert merged[0]["contract_name"] == "Pool_1_ETH"


def test_collect_mixer_rows_integration_fixture() -> None:
    md = (FIXTURES / "tornado_docs_sample.md").read_text(encoding="utf-8")
    disc = json.loads((FIXTURES / "privacy_pools_discovery_sample.json").read_text())
    rows = collect_mixer_rows(
        tornado_markdown=md,
        l2beat_discoveries={"privacy-pools": disc},
    )
    assert len(rows) == 6
