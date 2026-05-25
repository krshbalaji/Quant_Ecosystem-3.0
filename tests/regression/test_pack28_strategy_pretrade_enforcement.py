from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.strategy import (
    StrategyDefinition,
    strategy_registry,
)
from quant_ecosystem.strategy_execution import (
    strategy_execution_context,
)


class DummyMultiBroker:
    def place_order(self, **kwargs):
        return {
            "order_id": "TEST123",
            "success": True,
        }


def setup_function():
    strategy_registry.clear()
    strategy_execution_context.clear()


def test_strategy_tag_propagation():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="alpha_1",
            name="Alpha",
        )
    )

    router = ExecutionRouter()
    router._multi_broker = DummyMultiBroker()

    router.execute_canonical_order(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
        meta={
            "strategy_id": "alpha_1",
        },
    )

    owner = strategy_execution_context.get(
        "TEST123"
    )

    assert owner is not None
    assert owner["strategy_id"] == "alpha_1"


def test_plain_order_without_strategy():
    router = ExecutionRouter()
    router._multi_broker = DummyMultiBroker()

    result = router.execute_canonical_order(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=5,
    )

    assert result["order_id"] == "TEST123"