from pathlib import Path

from workers.token_taxonomy.defillama import (
    expand_dl_gecko_gap_rows,
    is_fiat_peg,
    parse_adapter_file,
)
from workers.token_taxonomy.parse import merge_taxonomy_rows

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "defillama_stablecoins"

SLUG_MAP = {
    "ethereum": 1,
    "polygon": 137,
    "bsc": 56,
    "arbitrum": 42161,
}


def test_is_fiat_peg() -> None:
    assert is_fiat_peg("peggedUSD") is True
    assert is_fiat_peg("peggedEUR") is True
    assert is_fiat_peg("peggedVAR") is False
    assert is_fiat_peg(None) is False


def test_parse_adapter_file_usdc() -> None:
    text = (FIXTURES / "usd-coin_config.ts").read_text(encoding="utf-8")
    rows, stats = parse_adapter_file(text, SLUG_MAP, "usd-coin", allowed=True)
    assert stats["parse_ok"] is True
    addrs = {(r["chain_id"], r["address"]) for r in rows}
    assert (1, "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48") in addrs
    assert (137, "0x2791bca1f2de4661ed88a30c99a7a9449aa84174") in addrs
    assert (137, "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf") not in addrs
    assert all(r["categories"] == ["stable"] for r in rows)


def test_parse_adapter_file_tether_excludes_bridge_on() -> None:
    text = (FIXTURES / "tether_config.ts").read_text(encoding="utf-8")
    rows, _ = parse_adapter_file(text, SLUG_MAP, "tether", allowed=True)
    addrs = {r["address"] for r in rows}
    assert "0xdac17f958d2ee523a2206206994597c13d831ec7" in addrs
    assert "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf" not in addrs
    assert all(a.startswith("0x") for a in addrs)


def test_expand_dl_gecko_gap_rows_only_missing() -> None:
    fiat = [{"gecko_id": "usd-coin", "pegType": "peggedUSD"}, {"gecko_id": "dai", "pegType": "peggedUSD"}]
    platforms = {
        "usd-coin": {"ethereum": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},
        "dai": {"ethereum": "0x6b175474e89094c44da98b954eedeac495271d0f"},
    }
    rows, _ = expand_dl_gecko_gap_rows(fiat, platforms, {"usd-coin"})
    gecko_ids = {r["gecko_id"] for r in rows}
    assert gecko_ids == {"dai"}
    assert all("stable" in r["categories"] for r in rows)


def test_merge_taxonomy_rows_unions_categories() -> None:
    cg = [
        {
            "chain_id": 1,
            "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "categories": ["meme"],
            "gecko_id": "usd-coin",
        }
    ]
    dl = [
        {
            "chain_id": 1,
            "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "categories": ["stable"],
            "gecko_id": "usd-coin",
        }
    ]
    merged = merge_taxonomy_rows(cg, dl)
    assert len(merged) == 1
    assert merged[0]["categories"] == ["meme", "stable"]
