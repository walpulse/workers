from __future__ import annotations

from datetime import date
from pathlib import Path

from workers.ofac_sdn.parse import (
    asset_symbol_from_feature_type,
    collect_ofac_rows,
    infer_blockchain,
    load_reference_data,
    normalize_address,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "sdn_advanced_sample.xml"


def test_asset_symbol_from_feature_type() -> None:
    assert asset_symbol_from_feature_type("Digital Currency Address - ETH") == "ETH"
    assert asset_symbol_from_feature_type("Email Address") == ""


def test_infer_blockchain_usdt() -> None:
    assert infer_blockchain("USDT", "0xabc") == "evm"
    assert infer_blockchain("USDT", "TXYZabcdefghijklmnopqrstuvwxyz123456") == "tron"


def test_normalize_evm_address() -> None:
    raw = "0xAbCdEf0123456789AbCdEf0123456789AbCdEf01"
    assert normalize_address("evm", raw) == raw.lower()


def test_load_reference_data_fixture() -> None:
    ft, programs, list_date = load_reference_data(SAMPLE)
    assert "345" in ft
    assert ft["345"] == "Digital Currency Address - ETH"
    assert programs["90001"] == ["SDGT"]
    assert list_date == date(2026, 8, 26)


def test_collect_ofac_rows_fixture() -> None:
    rows, list_date = collect_ofac_rows(SAMPLE)
    assert list_date == date(2026, 8, 26)
    assert len(rows) == 3

    eth = next(r for r in rows if r["asset_symbol"] == "ETH")
    assert eth["blockchain"] == "evm"
    assert eth["address"] == "0xabcdef0123456789abcdef0123456789abcdef01"
    assert eth["entity_name"] == "SANCTIONED ENTITY ALPHA"
    assert eth["programs"] == ["SDGT"]

    btc = next(r for r in rows if r["asset_symbol"] == "XBT")
    assert btc["blockchain"] == "bitcoin"
    assert btc["address"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

    usdt = next(r for r in rows if r["asset_symbol"] == "USDT")
    assert usdt["blockchain"] == "tron"
    assert usdt["entity_name"] == "SANCTIONED ENTITY BETA"
    assert usdt["programs"] == ["CYBER2"]
