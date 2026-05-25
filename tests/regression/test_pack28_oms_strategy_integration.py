from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.strategy import (
    StrategyDefinition,
    strategy_registry,
)


def setup_function():
    strategy_registry.clear()


def test_strategy_execution_runs():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="alpha_1",
            name="Alpha",
        )
    )

    router = ExecutionRouter()

    result = router.execute_canonical_order(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
        meta={"strategy_id": "alpha_1"},
    )

    assert "order_id" in result
    assert result["order_id"]


def test_plain_execution_runs():
    router = ExecutionRouter()

    result = router.execute_canonical_order(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=5,
    )

    assert "order_id" in result