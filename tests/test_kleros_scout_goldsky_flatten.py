from workers.kleros_scout_addresses.job import _flatten_litem


def test_flatten_litem_nested_metadata() -> None:
    raw = {
        "itemID": "0xabc",
        "status": "Registered",
        "latestRequestResolutionTime": "1",
        "metadata": {
            "key0": "eip155:1:0x" + "a" * 40,
            "key1": "Tag",
            "key2": "Project",
            "key3": "https://x.yz",
        },
    }
    flat = _flatten_litem(raw)
    assert flat["key0"].startswith("eip155:1:")
    assert flat["key1"] == "Tag"
    assert "metadata" not in flat
