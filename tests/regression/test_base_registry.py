from quant_ecosystem.core.base_registry import (
    BaseRegistry,
)


def test_register_and_get():

    registry = BaseRegistry[str, str]()

    registry.register("a", "alpha")

    assert registry.get("a") == "alpha"


def test_exists():

    registry = BaseRegistry[str, str]()

    registry.register("a", "alpha")

    assert registry.exists("a")


def test_count():

    registry = BaseRegistry[str, str]()

    registry.register("a", "alpha")
    registry.register("b", "beta")

    assert registry.count() == 2