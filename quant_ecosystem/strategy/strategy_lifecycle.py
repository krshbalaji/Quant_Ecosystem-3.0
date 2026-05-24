from quant_ecosystem.strategy.strategy_models import (
    StrategyHealth,
    StrategyState,
)

from quant_ecosystem.strategy.strategy_registry import (
    strategy_registry,
)


class StrategyLifecycle:

    def enable(
        self,
        strategy_id,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return None

        strategy.state = StrategyState.ENABLED
        return strategy

    def disable(
        self,
        strategy_id,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return None

        strategy.state = StrategyState.DISABLED
        return strategy

    def pause(
        self,
        strategy_id,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return None

        strategy.state = StrategyState.PAUSED
        return strategy

    def suspend(
        self,
        strategy_id,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return None

        strategy.state = StrategyState.SUSPENDED
        return strategy

    def set_health(
        self,
        strategy_id,
        health,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return None

        if isinstance(health, str):
            health = StrategyHealth[health]

        strategy.health = health
        return strategy

    def is_trade_allowed(
        self,
        strategy_id,
    ):
        strategy = strategy_registry.get(strategy_id)

        if not strategy:
            return False

        return strategy.is_active()


strategy_lifecycle = StrategyLifecycle()