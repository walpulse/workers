from __future__ import annotations

import json
from pathlib import Path

from workers.kleros_scout_addresses.parse import (
    collect_kleros_scout_rows,
    compute_source_hash,
    normalize_item,
    parse_caip10,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "kleros_scout_sample.json"


def test_parse_caip10_evm() -> None:
    assert parse_caip10("eip155:1:0x5E8422345238F34275888049021821E8E08CAa1f") == (
        1,
        "0x5e8422345238f34275888049021821e8e08caa1f",
    )
    assert parse_caip10("eip155:42161:0x2cb0e5abe11346679749063d3fbfc1f390e6e70a") == (
        42161,
        "0x2cb0e5abe11346679749063d3fbfc1f390e6e70a",
    )


def test_parse_caip10_invalid() -> None:
    assert parse_caip10("") is None
    assert parse_caip10("cosmos:osmosis-1:abc") is None
    assert parse_caip10("eip155:abc:0x1234") is None


def test_normalize_item_address_tag() -> None:
    raw = {
        "itemID": "0xabc",
        "status": "Registered",
        "key0": "eip155:1:0x5E8422345238F34275888049021821E8E08CAa1f",
        "key1": "Frax Ether Token",
        "key2": "Frax Finance",
        "key3": "https://app.frax.finance/frxeth/mint",
        "latestRequestResolutionTime": "1700610805",
    }
    row = normalize_item(raw, "address_tag")
    assert row is not None
    assert row["chain_id"] == 1
    assert row["name_tag"] == "Frax Ether Token"
    assert row["project_name"] == "Frax Finance"
    assert row["website"] == "https://app.frax.finance/frxeth/mint"
    assert row["source_updated_at"] is not None


def test_normalize_item_skips_bad_status() -> None:
    raw = {"itemID": "0x1", "status": "Rejected", "key0": "eip155:1:0x" + "a" * 40, "key1": "x"}
    assert normalize_item(raw, "address_tag") is None


def test_collect_kleros_scout_rows_fixture() -> None:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    rows = collect_kleros_scout_rows(data)
    assert len(rows) == 6
    registries = {r["registry"] for r in rows}
    assert registries == {"address_tag", "token", "contract_domain"}


def test_compute_source_hash_stable() -> None:
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    h1 = compute_source_hash(data)
    h2 = compute_source_hash(data)
    assert h1 == h2
    assert len(h1) == 64


def test_dedupe_by_chain_address_registry() -> None:
    dup = {
        "address_tag": [
            {
                "itemID": "0x1",
                "status": "Registered",
                "key0": "eip155:1:0x" + "a" * 40,
                "key1": "A",
                "key2": "P",
                "latestRequestResolutionTime": "1",
            },
            {
                "itemID": "0x2",
                "status": "Registered",
                "key0": "eip155:1:0x" + "a" * 40,
                "key1": "B",
                "key2": "P2",
                "latestRequestResolutionTime": "2",
            },
        ]
    }
    rows = collect_kleros_scout_rows(dup)
    assert len(rows) == 1
