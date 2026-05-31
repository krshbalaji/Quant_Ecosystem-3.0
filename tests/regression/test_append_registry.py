from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)


def test_append_registry():

    registry = AppendRegistry[str]()

    registry.register("a")
    registry.register("b")

    assert registry.count() == 2

    assert registry.entries() == [
        "a",
        "b",
    ]


def test_entries_returns_copy():

    registry = AppendRegistry[str]()

    registry.register("x")

    values = registry.entries()

    values.append("y")

    assert registry.count() == 1

    assert registry.entries() == [
        "x"
    ]