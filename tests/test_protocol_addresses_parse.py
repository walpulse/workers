"""Tests for protocol_addresses parsers (P0/P1/P2)."""

from __future__ import annotations

from pathlib import Path

from workers.protocol_addresses.parse import (
    DEFAULT_OFFICIAL_SEED,
    collect_defillama_protocol_rows,
    collect_protocol_rows,
    collect_spellbook_protocol_rows,
    load_official_seed,
    merge_protocol_rows,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_load_official_seed_min_rows():
    rows = load_official_seed(DEFAULT_OFFICIAL_SEED)
    assert len(rows) >= 50
    assert all(r["origin"] == "official" for r in rows)
    assert all(r["kind"] for r in rows)
    kinds = {r["kind"] for r in rows}
    assert "dex_factory" in kinds
    assert "aggregator" in kinds
    assert "lending" in kinds
    # LI.FI / Socket as aggregators
    protos = {r["protocol"] for r in rows}
    assert "lifi" in protos
    assert "socket" in protos


def test_merge_priority_official_wins():
    a = {
        "blockchain": "ethereum",
        "address": "0x" + "11" * 20,
        "protocol": "uniswap-v3",
        "kind": "dex_factory",
        "origin": "official",
        "contract_name": "Factory",
        "source_repo": "uniswap",
        "source_commit": "aaa",
    }
    b = {
        **a,
        "protocol": "other",
        "origin": "defillama",
        "source_repo": "defillama",
    }
    merged = merge_protocol_rows([b], [a])
    assert len(merged) == 1
    assert merged[0]["origin"] == "official"
    assert merged[0]["protocol"] == "uniswap-v3"


def test_spellbook_p1_fixture():
    labels_dir = FIXTURES / "spellbook_labels"
    if not labels_dir.is_dir():
        # reuse existing spellbook fixtures
        labels_dir = FIXTURES.parent / "fixtures" / "spellbook_labels"
    rows = collect_spellbook_protocol_rows(labels_dir)
    # bridges skipped; infrastructure / nft may appear
    assert isinstance(rows, list)
    assert all(r["origin"] == "spellbook" for r in rows)


def test_defillama_p2_fixture(tmp_path: Path):
    proj = tmp_path / "projects" / "uniswap"
    proj.mkdir(parents=True)
    (proj / "index.js").write_text(
        "module.exports = {\n"
        "  ethereum: {\n"
        "    factory: '0x1F98431c8aD98523631AE4a59f267346ea31F984',\n"
        "    router: '0xE592427A0AEce92De3Edee1F18E0157C05861564',\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    rows = collect_defillama_protocol_rows(
        tmp_path / "projects", allowlist={"uniswap"}
    )
    assert len(rows) >= 2
    assert all(r["origin"] == "defillama" for r in rows)
    assert {r["kind"] for r in rows} >= {"dex_factory", "dex_router"}


def test_collect_p0_only():
    rows = collect_protocol_rows(layers={"p0"})
    assert len(rows) >= 50
    addrs = [(r["blockchain"], r["address"]) for r in rows]
    assert len(addrs) == len(set(addrs))
