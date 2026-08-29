"""Tests for workers.mixer_addresses.parse."""

from __future__ import annotations

import json
from pathlib import Path

from workers.mixer_addresses.parse import (
    catalog_tier,
    collect_cyclone_docs_rows,
    collect_l2beat_rows_from_discovery,
    collect_mixer_rows,
    collect_railgun_deployment_rows,
    collect_tornado_docs_rows,
    collect_typhoon_seed_rows,
    merge_mixer_rows,
    normalize_evm_address,
    parse_l2beat_address,
    parse_railgun_proxy_from_ts,
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
    assert all(r["catalog_tier"] == "canonical" for r in rows)


def test_privacy_mechanism_and_tier_by_protocol() -> None:
    assert privacy_mechanism("tornado-cash") == "zk_pool"
    assert privacy_mechanism("umbra") == "stealth"
    assert privacy_mechanism("zama-cw") == "fhe_wrapper"
    assert privacy_mechanism("privacy-boost") == "tee"
    assert privacy_mechanism("cyclone") == "zk_pool"
    assert catalog_tier("tornado-cash") == "canonical"
    assert catalog_tier("railgun") == "canonical"
    assert catalog_tier("cyclone") == "fork"
    assert catalog_tier("typhoon-cash") == "fork"


def test_collect_l2beat_privacy_pools_fixture() -> None:
    disc = json.loads((FIXTURES / "privacy_pools_discovery_sample.json").read_text())
    rows = collect_l2beat_rows_from_discovery("privacy-pools", disc)
    assert len(rows) == 2
    names = {r["contract_name"] for r in rows}
    assert names == {"PrivacyPoolUSDS", "PrivacyPoolsEntrypoint"}
    assert all(r["source"] == "l2beat" for r in rows)
    assert all(r["privacy_mechanism"] == "zk_pool" for r in rows)
    assert all(r["catalog_tier"] == "canonical" for r in rows)


def test_merge_prefers_later_on_collision() -> None:
    tornado = [
        {
            "blockchain": "ethereum",
            "address": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
            "protocol": "tornado-cash",
            "protocol_name": "Tornado Cash",
            "contract_name": "1 ETH",
            "contract_role": "pool",
            "privacy_mechanism": "zk_pool",
            "catalog_tier": "canonical",
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
            "catalog_tier": "canonical",
            "asset_symbol": None,
            "denomination": None,
            "source": "l2beat",
        }
    ]
    merged = merge_mixer_rows(tornado, l2beat)
    assert len(merged) == 1
    assert merged[0]["source"] == "l2beat"
    assert merged[0]["contract_name"] == "Pool_1_ETH"


def test_railgun_proxy_parse_and_rows() -> None:
    ts = (FIXTURES / "railgun_ethereum_sample.ts").read_text(encoding="utf-8")
    assert (
        parse_railgun_proxy_from_ts(ts)
        == "0xfa7093cdd9ee6932b4eb2c9e1cde7ce00b1fa4b9"
    )
    rows = collect_railgun_deployment_rows({"ethereum": ts, "polygon": ""})
    assert len(rows) == 1
    assert rows[0]["blockchain"] == "ethereum"
    assert rows[0]["source"] == "railgun-deployments"
    assert rows[0]["catalog_tier"] == "canonical"


def test_cyclone_docs_fixture_evm_only() -> None:
    md = (FIXTURES / "cyclone_docs_sample.md").read_text(encoding="utf-8")
    rows = collect_cyclone_docs_rows(md)
    chains = {r["blockchain"] for r in rows}
    assert chains == {"ethereum", "bsc", "polygon"}
    assert len(rows) == 7
    assert all(r["catalog_tier"] == "fork" for r in rows)
    assert all(r["protocol"] == "cyclone" for r in rows)
    assert not any(r["address"].startswith("io") for r in rows)


def test_typhoon_seed_requires_three_pools(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text('{"pools": []}', encoding="utf-8")
    assert collect_typhoon_seed_rows(empty) == []

    two = tmp_path / "two.json"
    two.write_text(
        json.dumps(
            {
                "pools": [
                    {
                        "blockchain": "ethereum",
                        "address": "0x1111111111111111111111111111111111111111",
                        "contract_name": "A",
                    },
                    {
                        "blockchain": "ethereum",
                        "address": "0x2222222222222222222222222222222222222222",
                        "contract_name": "B",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    assert collect_typhoon_seed_rows(two) == []


def test_collect_mixer_rows_integration_fixture() -> None:
    md = (FIXTURES / "tornado_docs_sample.md").read_text(encoding="utf-8")
    disc = json.loads((FIXTURES / "privacy_pools_discovery_sample.json").read_text())
    cyclone = (FIXTURES / "cyclone_docs_sample.md").read_text(encoding="utf-8")
    railgun_ts = (FIXTURES / "railgun_ethereum_sample.ts").read_text(encoding="utf-8")
    rows = collect_mixer_rows(
        tornado_markdown=md,
        l2beat_discoveries={"privacy-pools": disc},
        railgun_chain_sources={"ethereum": railgun_ts},
        cyclone_markdown=cyclone,
    )
    assert len(rows) >= 6 + 7 + 1
    assert any(r["protocol"] == "cyclone" for r in rows)
    assert any(r["source"] == "railgun-deployments" for r in rows)
