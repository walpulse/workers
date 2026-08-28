import json
from pathlib import Path

from workers.token_taxonomy.parse import (
    build_gecko_tag_map,
    compute_source_hash,
    expand_platform_rows,
    normalize_evm_address,
    parse_bluechip_ids,
    parse_coins_list,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "token_taxonomy"


def test_normalize_evm_address() -> None:
    assert normalize_evm_address("0xAbC0000000000000000000000000000000000000") == (
        "0xabc0000000000000000000000000000000000000"
    )
    assert normalize_evm_address("not-an-address") is None


def test_build_gecko_tag_map_bluechip_excludes_stable_meme() -> None:
    categories = {
        "stablecoins": ["usd-coin"],
        "meme-token": ["pepe"],
    }
    bluechip = ["usd-coin", "pepe", "bitcoin"]
    tags = build_gecko_tag_map(categories, bluechip)
    assert tags["usd-coin"] == {"stable"}
    assert tags["pepe"] == {"meme"}
    assert tags["bitcoin"] == {"bluechip"}


def test_expand_platform_rows() -> None:
    list_payload = json.loads((FIXTURES / "coins_list_sample.json").read_text(encoding="utf-8"))
    platforms = parse_coins_list(list_payload)
    gecko_tags = {
        "usd-coin": {"stable"},
        "pepe": {"meme"},
    }
    rows, stats = expand_platform_rows(gecko_tags, platforms)
    assert len(rows) == 3
    eth_usdc = next(r for r in rows if r["chain_id"] == 1 and r["address"].endswith("6eb48"))
    assert eth_usdc["categories"] == ["stable"]
    assert eth_usdc["gecko_id"] == "usd-coin"
    assert stats["skipped_platform"] >= 0


def test_parse_bluechip_ids() -> None:
    payload = json.loads((FIXTURES / "markets_bluechip_sample.json").read_text(encoding="utf-8"))
    ids = parse_bluechip_ids(payload, max_rank=100)
    assert ids == ["bitcoin", "usd-coin", "pepe"]


def test_compute_source_hash_stable() -> None:
    a = compute_source_hash({"meme-token": ["a"]}, ["b"], 100)
    b = compute_source_hash({"meme-token": ["a"]}, ["b"], 100)
    c = compute_source_hash({"meme-token": ["a"]}, ["b"], 101)
    assert a == b
    assert a != c


def test_merge_multi_tag_on_same_address() -> None:
    gecko_tags = {"usd-coin": {"stable", "airdrop"}}
    platforms = {"usd-coin": {"ethereum": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"}}
    rows, _ = expand_platform_rows(gecko_tags, platforms)
    assert rows[0]["categories"] == ["airdrop", "stable"]
