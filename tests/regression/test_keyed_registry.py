from quant_ecosystem.core.keyed_registry import (
    KeyedRegistry,
)


def test_keyed_registry():

    registry = KeyedRegistry[str, int]()

    registry.register(
        "A",
        10,
    )

    assert registry.exists("A")
    assert registry.get("A") == 10
    assert registry.count() == 1