from quant_ecosystem.execution.broker_registry import (
    BrokerRegistry,
)

from quant_ecosystem.execution.broker_failover import (
    BrokerFailover,
)


def test_failover():
    reg = BrokerRegistry()

    b1 = object()
    b2 = object()

    reg.register("a", b1)
    reg.register("b", b2)

    failover = BrokerFailover()

    name, broker = failover.failover(
        reg,
        failed_name="a",
    )

    assert name == "b"
    assert broker is b2