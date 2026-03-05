from __future__ import annotations

from copy import deepcopy
from typing import Dict, Type

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy


class StrategyFactory:
    """
    Central factory for creating and cloning strategies.
    """

    def __init__(self, registry=None):
        self.registry = registry

    def create(self, cls: Type[BaseStrategy], params: Dict[str, object] | None = None) -> BaseStrategy:
        """
        Instantiate a new strategy from a class and params.
        """
        return cls(params=params or {})

    def clone(self, strategy: BaseStrategy) -> BaseStrategy:
        """
        Create a deep copy of a strategy instance.
        """
        cls: Type[BaseStrategy] = type(strategy)
        params_copy = deepcopy(strategy.params)
        clone = cls(params=params_copy)
        clone.required_timeframes = list(strategy.required_timeframes)
        clone.required_symbols = list(strategy.required_symbols)
        return clone

    def mutate_numeric_params(
        self,
        strategy: BaseStrategy,
        low: float = 0.9,
        high: float = 1.1,
    ) -> BaseStrategy:
        """
        Return a new strategy with numeric params scaled by a random factor.
        """
        from random import uniform

        mutated = self.clone(strategy)
        for key, value in list(mutated.params.items()):
            if isinstance(value, (int, float)):
                factor = uniform(low, high)
                mutated.params[key] = value * factor
        return mutated

