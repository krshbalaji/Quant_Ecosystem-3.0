import random


class AlphaEvolutionEngine:
    """
    Strategy mutation and evolution engine.
    Creates new strategies from top performers.
    """

    def __init__(self, strategy_registry):

        self.strategy_registry = strategy_registry

    def evolve(self):

        strategies = self._get_strategies()

        if not strategies:
            print("AlphaEvolution: no strategies available")
            return []

        # Sort by score in descending order. Supports both dict-style
        # registry entries and plain strategy objects.
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

    def _mutate(self, strategy_entry):
        """
        Create a mutated child strategy.

        Accepts either a plain strategy instance or a registry entry dict
        of the shape {"id": ..., "strategy": ..., "score": ...}.
        """
        if isinstance(strategy_entry, dict):
            base = strategy_entry.get("strategy")
            base_id = strategy_entry.get("id", getattr(base, "name", "strategy"))
        else:
            base = strategy_entry
            base_id = getattr(strategy_entry, "name", "strategy")

        if base is None:
            return strategy_entry

        params = getattr(base, "params", {}).copy()

        for k in params:
            if isinstance(params[k], (int, float)):
                params[k] *= random.uniform(0.9, 1.1)

        new_strategy = type(base)()
        new_strategy.params = params
        new_strategy.name = f"{base_id}_mut"

        # Return a registry-style entry so downstream components can store it.
        return {
            "id": new_strategy.name,
            "strategy": new_strategy,
            "parent_id": base_id,
        }

    def _get_strategies(self):

        if hasattr(self.strategy_registry, "get_all"):
            return self.strategy_registry.get_all()

        if hasattr(self.strategy_registry, "strategies"):
            return list(self.strategy_registry.strategies.values())

        return []

    # Unified interface helper
    def run(self):
        """
        Generic entry point expected by orchestration layers.
        """
        return self.evolve()