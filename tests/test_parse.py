from __future__ import annotations

from pathlib import Path

from workers.cex_addresses.parse import (
    collect_cex_rows,
    is_values_seed_file,
    parse_chain_values,
    parse_evm_values,
    parse_sql_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_evm_normalizes_address_case() -> None:
    text = (FIXTURES / "cex_evms_addresses.sql").read_text(encoding="utf-8")
    rows = parse_evm_values(text)
    assert len(rows) == 3
    assert rows[0]["blockchain"] == "evm"
    assert rows[0]["address"] == "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be"
    assert rows[1]["address"] == "0xd551234ae421e3bcba99a0da6d736074f22192ff"
    assert rows[2]["cex_name"] == "Coinbase"


def test_parse_chain_bitcoin() -> None:
    text = (FIXTURES / "cex_bitcoin_addresses.sql").read_text(encoding="utf-8")
    rows = parse_chain_values(text)
    assert len(rows) == 2
    assert rows[0]["blockchain"] == "bitcoin"
    assert rows[0]["address"].startswith("1Cb1")
    assert rows[1]["cex_name"] == "Binance"


def test_wrapper_not_values_seed() -> None:
    path = FIXTURES / "cex_ethereum_addresses_wrapper.sql"
    assert is_values_seed_file(path) is False


def test_collect_from_fixture_tree(tmp_path: Path) -> None:
    root = tmp_path / "addresses"
    chains = root / "chains"
    chains.mkdir(parents=True)
    (chains / "cex_evms_addresses.sql").write_text(
        (FIXTURES / "cex_evms_addresses.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    btc = chains / "bitcoin"
    btc.mkdir()
    (btc / "cex_bitcoin_addresses.sql").write_text(
        (FIXTURES / "cex_bitcoin_addresses.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    eth = chains / "ethereum"
    eth.mkdir()
    (eth / "cex_ethereum_addresses.sql").write_text(
        (FIXTURES / "cex_ethereum_addresses_wrapper.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rows = collect_cex_rows(root)
    assert len(rows) == 5  # 3 evm + 2 bitcoin
    assert sum(1 for r in rows if r["blockchain"] == "evm") == 3
    assert sum(1 for r in rows if r["blockchain"] == "bitcoin") == 2


def test_parse_sql_file_dispatch() -> None:
    evm = parse_sql_file(FIXTURES / "cex_evms_addresses.sql")
    btc = parse_sql_file(FIXTURES / "cex_bitcoin_addresses.sql")
    assert all(r["blockchain"] == "evm" for r in evm)
    assert all(r["blockchain"] == "bitcoin" for r in btc)
