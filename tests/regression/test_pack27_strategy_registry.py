from quant_ecosystem.strategy import (
    StrategyDefinition,
    StrategyHealth,
    StrategyState,
    strategy_lifecycle,
    strategy_registry,
)


def setup_function():
    strategy_registry.clear()


def test_register_strategy():
    s = StrategyDefinition(
        strategy_id="momentum_1",
        name="Momentum Strategy",
    )

    strategy_registry.register(s)

    assert strategy_registry.exists("momentum_1")


def test_disable_strategy():
    s = StrategyDefinition(
        strategy_id="mr_1",
        name="Mean Reversion",
    )

    strategy_registry.register(s)

    strategy_lifecycle.disable("mr_1")

    assert (
        strategy_registry.get("mr_1").state
        == StrategyState.DISABLED
    )


def test_pause_strategy():
    s = StrategyDefinition(
        strategy_id="opt_hedge",
        name="Option Hedge",
    )

    strategy_registry.register(s)

    strategy_lifecycle.pause("opt_hedge")

    assert (
        strategy_registry.get("opt_hedge").state
        == StrategyState.PAUSED
    )


def test_failed_strategy_not_tradeable():
    s = StrategyDefinition(
        strategy_id="broken",
        name="Broken Strategy",
    )

    strategy_registry.register(s)

    strategy_lifecycle.set_health(
        "broken",
        StrategyHealth.FAILED,
    )

    assert (
        strategy_lifecycle.is_trade_allowed(
            "broken"
        )
        is False
    )


def test_enabled_strategy_tradeable():
    s = StrategyDefinition(
        strategy_id="live_alpha",
        name="Live Alpha",
    )

    strategy_registry.register(s)

    assert (
        strategy_lifecycle.is_trade_allowed(
            "live_alpha"
        )
        is True
    )