from quant_ecosystem.execution.broker_registry import (
    BrokerRegistry,
)

from quant_ecosystem.execution.routing.broker_health_router import (
    BrokerHealthRouter,
)


def test_health_selection():
    reg = BrokerRegistry()

    reg.register("a", object())
    reg.register("b", object())

    router = BrokerHealthRouter()

    router.mark_unhealthy("a")

    name, _ = router.select_healthy(reg)

    assert name == "b"


def test_preferred_if_healthy():
    reg = BrokerRegistry()

    reg.register("x", object())

    router = BrokerHealthRouter()

    name, _ = router.select_healthy(
        reg,
        preferred="x",
    )

    assert name == "x"