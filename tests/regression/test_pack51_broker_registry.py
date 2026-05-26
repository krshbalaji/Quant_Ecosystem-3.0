from quant_ecosystem.execution.broker_registry import (
    BrokerRegistry,
)


def test_register_lookup():
    reg = BrokerRegistry()

    broker = object()

    reg.register(
        "fyers",
        broker,
    )

    assert reg.get("fyers") is broker


def test_all():
    reg = BrokerRegistry()

    reg.register(
        "a",
        object(),
    )

    reg.register(
        "b",
        object(),
    )

    assert len(reg.all()) == 2