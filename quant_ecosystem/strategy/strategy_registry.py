from quant_ecosystem.strategy.strategy_models import (
    StrategyDefinition,
)


class StrategyRegistry:

    def __init__(self):
        self._strategies = {}

    def register(
        self,
        strategy: StrategyDefinition,
    ):
        self._strategies[
            strategy.strategy_id
        ] = strategy

        return strategy

    def get(
        self,
        strategy_id,
    ):
        return self._strategies.get(strategy_id)

    def exists(
        self,
        strategy_id,
    ):
        return strategy_id in self._strategies

    def remove(
        self,
        strategy_id,
    ):
        self._strategies.pop(strategy_id, None)

    def list_all(self):
        return list(self._strategies.values())

    def clear(self):
        self._strategies.clear()


strategy_registry = StrategyRegistry()