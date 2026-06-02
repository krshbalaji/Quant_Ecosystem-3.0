from quant_ecosystem.core.multimap_store import MultiMapStore


def test_multimap_put_get_latest_keys_size():
    s = MultiMapStore()
    assert s.keys() == []
    assert s.size() == 0

    s.put("k1", 1)
    s.put("k1", 2)
    s.put("k2", "a")

    assert set(s.keys()) == {"k1", "k2"}
    assert s.size() == 3
    assert s.get("k1") == [1, 2]
    assert s.latest("k1") == 2
    assert s.latest("missing") is None
