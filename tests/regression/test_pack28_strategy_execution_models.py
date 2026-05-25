from quant_ecosystem.strategy_execution import (
    StrategyExecutionIntent,
    StrategyRiskBudget,
    strategy_execution_context,
)


def setup_function():
    strategy_execution_context.clear()


def test_execution_intent():
    intent = StrategyExecutionIntent(
        strategy_id="alpha_1",
        symbol="NIFTY",
        side="BUY",
        qty=10,
        price=100,
    )

    assert (
        intent.execution_notional()
        == 1000
    )


def test_risk_budget_remaining():
    rb = StrategyRiskBudget(
        strategy_id="alpha_1",
        max_capital=100000,
        current_capital_used=25000,
    )

    assert (
        rb.remaining_capital
        == 75000
    )


def test_risk_budget_total_pnl():
    rb = StrategyRiskBudget(
        strategy_id="alpha_1",
        realized_pnl=500,
        unrealized_pnl=-100,
    )

    assert rb.total_pnl == 400


def test_strategy_context_attach():
    strategy_execution_context.attach(
        order_id="ORD1",
        strategy_id="momentum",
    )

    assert (
        strategy_execution_context.strategy_for_order(
            "ORD1"
        )
        == "momentum"
    )


def test_strategy_context_remove():
    strategy_execution_context.attach(
        order_id="ORD2",
        strategy_id="hedge",
    )

    strategy_execution_context.remove("ORD2")

    assert (
        strategy_execution_context.get("ORD2")
        is None
    )