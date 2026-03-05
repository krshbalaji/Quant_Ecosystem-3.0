import random
from typing import List

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy
from quant_ecosystem.strategies.factory.strategy_factory import StrategyFactory


class AlphaEvolutionEngine:
    """
    Strategy mutation and evolution engine.
    Creates new strategies from top performers.
    """

    def __init__(self, strategy_registry, factory: StrategyFactory | None = None):
        self.strategy_registry = strategy_registry
        self.factory = factory or StrategyFactory(strategy_registry)

    def evolve(self):

        strategies = self._get_strategies()

        if not strategies:
            print("AlphaEvolution: no strategies available")
            return []

        # Sort by score in descending order. Supports both legacy dict-style
        # registry entries and class-based strategies.
        def _score(entry):
            if isinstance(entry, dict):
                return entry.get("score", 0)
            return getattr(entry, "score", 0)

        parents = sorted(strategies, key=_score, reverse=True)[:3]

        children = []

        for p in parents:

            child = self._mutate(p)
            children.append(child)

        print(f"AlphaEvolution: created {len(children)} new strategies")

        return children

    def _mutate(self, strategy_entry: BaseStrategy | dict) -> BaseStrategy:
        """
        Create a mutated child strategy.

        Mutates only numeric params and delegates instance creation to
        StrategyFactory. Core logic (class type) is never changed.
        """
        if isinstance(strategy_entry, dict):
            base = strategy_entry.get("strategy")
        else:
            base = strategy_entry

        if base is None:
            return strategy_entry  # type: ignore[return-value]

        if not (hasattr(base, "params") and hasattr(base, "id")):
            return strategy_entry  # type: ignore[return-value]

        child = self.factory.mutate_numeric_params(base)
        child.id = f"{base.id}_mut"
        child.name = f"{base.name} (mut)"
        return child

    def _get_strategies(self) -> List[BaseStrategy | dict]:
        raw = None
        if hasattr(self.strategy_registry, "get_all"):
            raw = self.strategy_registry.get_all()
        elif hasattr(self.strategy_registry, "strategies"):
            raw = self.strategy_registry.strategies

        if raw is None:
            return []

        if isinstance(raw, dict):
            return list(raw.values())
        return list(raw)

    # Unified interface helper
    def run(self):
        """
        Generic entry point expected by orchestration layers.
        """
        return self.evolve()