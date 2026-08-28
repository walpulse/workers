from __future__ import annotations

from pathlib import Path

from workers.cex_addresses.parse import collect_cex_rows
from workers.spellbook_labels.parse import (
    cex_rows_to_labels,
    collect_spellbook_label_rows,
    parse_label_values,
    row_key,
    should_skip_label_file,
)

FIXTURES = Path(__file__).parent / "fixtures" / "spellbook_labels"
CEX_FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_stablecoins_values() -> None:
    text = (FIXTURES / "labels_stablecoins.sql").read_text(encoding="utf-8")
    rows = parse_label_values(text)
    assert len(rows) >= 50
    usdt = next(r for r in rows if r["address"] == "0xdac17f958d2ee523a2206206994597c13d831ec7")
    assert usdt["blockchain"] == "ethereum"
    assert usdt["category"] == "infrastructure"
    assert usdt["model_name"] == "stablecoins"
    assert usdt["label_type"] == "identifier"
    assert usdt["source"] == "static"


def test_parse_bridges_ethereum_date() -> None:
    text = (FIXTURES / "labels_bridges_ethereum.sql").read_text(encoding="utf-8")
    rows = parse_label_values(text)
    assert len(rows) >= 10
    row = next(r for r in rows if "Across Protocol: Bridge Admin" in r["name"])
    assert row["blockchain"] == "ethereum"
    assert row["category"] == "bridge"
    assert row["created_at"] == "2022-09-22T00:00:00Z"
    assert row["model_name"] == "bridges_ethereum"


def test_skip_query_contracts_model() -> None:
    path = FIXTURES / "labels_contracts.sql"
    assert should_skip_label_file(path) is True


def test_cex_rows_to_labels(tmp_path: Path) -> None:
    chains = tmp_path / "chains"
    chains.mkdir(parents=True)
    (chains / "cex_evms_addresses.sql").write_text(
        (CEX_FIXTURES / "cex_evms_addresses.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cex_rows = collect_cex_rows(chains)
    labels = cex_rows_to_labels(cex_rows)
    assert len(labels) == 3
    assert labels[0]["category"] == "institution"
    assert labels[0]["model_name"].startswith("cex_")
    assert labels[0]["label_type"] == "identifier"


def test_collect_dedup_by_pk(tmp_path: Path) -> None:
    labels_root = tmp_path / "labels"
    infra = labels_root / "infrastructure" / "identifier" / "stablecoins"
    infra.mkdir(parents=True)
    (infra / "labels_stablecoins.sql").write_text(
        (FIXTURES / "labels_stablecoins.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    bridge = labels_root / "bridge" / "identifiers"
    bridge.mkdir(parents=True)
    (bridge / "labels_bridges_ethereum.sql").write_text(
        (FIXTURES / "labels_bridges_ethereum.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    rows = collect_spellbook_label_rows(labels_root)
    keys = [row_key(r) for r in rows]
    assert len(keys) == len(set(keys))
