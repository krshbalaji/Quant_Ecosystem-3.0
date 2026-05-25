from quant_ecosystem.strategy import (
    StrategyDefinition,
    strategy_registry,
)

from quant_ecosystem.strategy_execution import (
    StrategyRiskBudget,
    strategy_risk_controller,
)


def setup_function():
    strategy_registry.clear()
    strategy_risk_controller.clear()


def test_capital_limit():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="alpha",
            name="Alpha",
        )
    )

    strategy_risk_controller.register_budget(
        StrategyRiskBudget(
            strategy_id="alpha",
            max_capital=10000,
            current_capital_used=9000,
        )
    )

    allowed, reason = (
        strategy_risk_controller.validate(
            "alpha",
            proposed_notional=2000,
        )
    )

    assert allowed is False
    assert reason == "STRATEGY_CAPITAL_LIMIT"


def test_position_limit():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="beta",
            name="Beta",
        )
    )

    strategy_risk_controller.register_budget(
        StrategyRiskBudget(
            strategy_id="beta",
            max_positions=2,
            current_positions=2,
        )
    )

    allowed, reason = (
        strategy_risk_controller.validate(
            "beta"
        )
    )

    assert allowed is False
    assert reason == "STRATEGY_POSITION_LIMIT"


def test_max_loss():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="gamma",
            name="Gamma",
        )
    )

    strategy_risk_controller.register_budget(
        StrategyRiskBudget(
            strategy_id="gamma",
            max_loss=5000,
            realized_pnl=-6000,
        )
    )

    allowed, reason = (
        strategy_risk_controller.validate(
            "gamma"
        )
    )

    assert allowed is False
    assert reason == "STRATEGY_MAX_LOSS"


def test_kill_switch():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="delta",
            name="Delta",
        )
    )

    strategy_risk_controller.enable_kill_switch(
        "delta"
    )

    allowed, reason = (
        strategy_risk_controller.validate(
            "delta"
        )
    )

    assert allowed is False
    assert reason == "STRATEGY_KILL_SWITCH"


def test_reject_streak_pause():
    strategy_registry.register(
        StrategyDefinition(
            strategy_id="eps",
            name="Epsilon",
        )
    )

    strategy_risk_controller.record_reject(
        "eps"
    )
    strategy_risk_controller.record_reject(
        "eps"
    )
    strategy_risk_controller.record_reject(
        "eps"
    )

    allowed, reason = (
        strategy_risk_controller.validate(
            "eps"
        )
    )

    assert allowed is False