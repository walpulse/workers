"""Tests for bridge_addresses parse collectors."""

from __future__ import annotations

import json
from pathlib import Path

from workers.bridge_addresses.parse import (
    collect_across_rows,
    collect_axelar_rows,
    collect_bridge_rows,
    collect_ccip_rows,
    collect_defillama_rows,
    collect_hop_rows,
    collect_stargate_lz_rows,
    collect_wormhole_rows,
    merge_bridge_rows,
    normalize_address,
    normalize_evm_address,
)

FIXTURES = Path(__file__).parent / "fixtures"
DEFILLAMA = FIXTURES / "defillama_sample"


def test_normalize_evm_address_lowercase():
    assert normalize_evm_address("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2") == (
        "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    )


def test_normalize_address_solana_passthrough():
    addr = "Ccip842gzYHhvdDkSyi2YVCoAWPbYJoApMFzSxQroE9C"
    assert normalize_address("solana", addr) == addr


def test_collect_hop_rows_from_fixture():
    text = (FIXTURES / "hop_adapter_sample.ts").read_text(encoding="utf-8")
    rows = collect_hop_rows(text)
    assert len(rows) >= 20
    assert all(r["bridge_slug"] == "hop" for r in rows)
    assert all(r["source"] == "hop-addresses" for r in rows)


def test_collect_stargate_rows_from_fixture():
    payload = json.loads((FIXTURES / "stargate_metadata_sample.json").read_text(encoding="utf-8"))
    rows = collect_stargate_lz_rows(payload)
    assert len(rows) >= 50
    assert any(r["contract_role"] == "pool" for r in rows)


def test_collect_wormhole_rows_from_fixture():
    text = (FIXTURES / "wormhole_consts_sample.ts").read_text(encoding="utf-8")
    rows = collect_wormhole_rows(text)
    assert len(rows) >= 30
    eth = [r for r in rows if r["blockchain"] == "ethereum"]
    assert any(r["contract_role"] == "core" for r in eth)
    assert any(r["contract_role"] == "token_bridge" for r in eth)


def test_collect_defillama_rows_from_fixture():
    network = (DEFILLAMA / "src/data/bridgeNetworkData.ts").read_text(encoding="utf-8")
    rows = collect_defillama_rows(DEFILLAMA / "src/adapters", network)
    assert len(rows) >= 30
    assert any(r["bridge_slug"] == "hop" for r in rows)


def test_collect_ccip_rows_from_fixture():
    payload = json.loads((FIXTURES / "ccip_chains_sample.json").read_text(encoding="utf-8"))
    rows = collect_ccip_rows(payload)
    assert len(rows) >= 30
    assert all(r["bridge_slug"] == "ccip" for r in rows)


def test_collect_across_rows_from_fixture():
    payload = json.loads((FIXTURES / "across_addresses_sample.json").read_text(encoding="utf-8"))
    rows = collect_across_rows(payload)
    assert len(rows) >= 20
    assert any(r["contract_role"] == "spoke_pool" for r in rows)


def test_collect_axelar_rows_from_fixture():
    payload = json.loads((FIXTURES / "axelar_config_sample.json").read_text(encoding="utf-8"))
    rows = collect_axelar_rows(payload)
    assert len(rows) >= 10
    assert any(r["contract_name"] == "AxelarGateway" for r in rows)


def test_merge_bridge_rows_priority():
    official = [
        {
            "blockchain": "ethereum",
            "address": "0xabcdef0123456789012345678901234567890ab",
            "bridge_slug": "across",
            "bridge_name": "Across",
            "contract_name": "SpokePool",
            "contract_role": "spoke_pool",
            "asset_symbol": None,
            "source": "across-docs",
        }
    ]
    defillama = [
        {
            "blockchain": "ethereum",
            "address": "0xabcdef0123456789012345678901234567890ab",
            "bridge_slug": "hop",
            "bridge_name": "Hop",
            "contract_name": "x",
            "contract_role": "gateway",
            "asset_symbol": None,
            "source": "defillama",
        }
    ]
    merged = merge_bridge_rows(defillama, official)
    assert len(merged) == 1
    assert merged[0]["source"] == "across-docs"


def test_collect_bridge_rows_integration():
    network = (DEFILLAMA / "src/data/bridgeNetworkData.ts").read_text(encoding="utf-8")
    rows = collect_bridge_rows(
        defillama_adapters_dir=DEFILLAMA / "src/adapters",
        bridge_network_data=network,
        stargate_payload=json.loads(
            (FIXTURES / "stargate_metadata_sample.json").read_text(encoding="utf-8")
        ),
        wormhole_consts=(FIXTURES / "wormhole_consts_sample.ts").read_text(encoding="utf-8"),
        hop_adapter_text=(FIXTURES / "hop_adapter_sample.ts").read_text(encoding="utf-8"),
        ccip_payload=json.loads((FIXTURES / "ccip_chains_sample.json").read_text(encoding="utf-8")),
        across_payload=json.loads(
            (FIXTURES / "across_addresses_sample.json").read_text(encoding="utf-8")
        ),
        axelar_payload=json.loads((FIXTURES / "axelar_config_sample.json").read_text(encoding="utf-8")),
    )
    assert len(rows) >= 150
    keys = {(r["blockchain"], r["address"]) for r in rows}
    assert len(keys) == len(rows)
