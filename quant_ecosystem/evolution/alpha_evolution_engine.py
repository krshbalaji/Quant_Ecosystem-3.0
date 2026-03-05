import random


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

    def _mutate(self, strategy):

        params = getattr(strategy, "params", {}).copy()

        for k in params:

            if isinstance(params[k], (int, float)):
                params[k] *= random.uniform(0.9, 1.1)

        new_strategy = type(strategy)()

        new_strategy.params = params
        new_strategy.name = strategy.name + "_mut"

        return new_strategy

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