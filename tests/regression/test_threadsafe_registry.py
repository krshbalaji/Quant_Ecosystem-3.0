from quant_ecosystem.core.base_registry import (
    BaseRegistry,
)
from quant_ecosystem.core.registry_threading import (
    ThreadSafeRegistry,
)


def test_threadsafe_registry():

    registry = ThreadSafeRegistry[str, str]()

    registry.register("a", "alpha")

    assert registry.get("a") == "alpha"


def test_snapshot():

    registry = ThreadSafeRegistry[str, str]()

    registry.register("a", "alpha")

    snapshot = registry.snapshot()

    assert snapshot["a"] == "alpha"