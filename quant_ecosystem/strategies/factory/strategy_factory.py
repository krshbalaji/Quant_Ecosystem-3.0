from __future__ import annotations

from copy import deepcopy
from typing import Dict, Type

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy


class StrategyFactory:
    """
    Central factory for creating, cloning and mutating strategies.
    """

    def __init__(self, registry=None):
        self.registry = registry

    def create_from_class(self, cls: Type[BaseStrategy], params: Dict[str, object] | None = None) -> BaseStrategy:
        """
        Instantiate a new strategy from a concrete strategy class and params.
        """
        return cls(params=params or {})

    # Backwards-compat alias
    create = create_from_class

    def clone(self, strategy: BaseStrategy) -> BaseStrategy:
        """
        Create a deep copy of a strategy instance without re-running __init__.
        """
        return deepcopy(strategy)

    def mutate(
        self,
        strategy: BaseStrategy,
        low: float = 0.9,
        high: float = 1.1,
    ) -> BaseStrategy:
        """
        Return a new strategy with numeric params scaled by a random factor.
        Core logic (class type) is preserved.
        """
        from random import uniform

        mutated = self.clone(strategy)
        for key, value in list(mutated.params.items()):
            if isinstance(value, (int, float)):
                factor = uniform(low, high)
                mutated.params[key] = value * factor
        return mutated
