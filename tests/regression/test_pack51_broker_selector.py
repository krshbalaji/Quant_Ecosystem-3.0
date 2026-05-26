from quant_ecosystem.execution.broker_registry import (
    BrokerRegistry,
)

from quant_ecosystem.execution.broker_selector import (
    BrokerSelector,
)


def test_select_preferred():
    reg = BrokerRegistry()

    broker = object()

    reg.register("fyers", broker)

    selector = BrokerSelector()

    name, chosen = selector.select(
        reg,
        preferred="fyers",
    )

    assert name == "fyers"
    assert chosen is broker


def test_select_first():
    reg = BrokerRegistry()

    broker = object()

    reg.register("a", broker)

    selector = BrokerSelector()

    name, chosen = selector.select(reg)

    assert name == "a"
    assert chosen is broker