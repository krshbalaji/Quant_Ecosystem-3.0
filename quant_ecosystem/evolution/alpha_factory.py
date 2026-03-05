from quant_ecosystem.evolution.strategy_genome import StrategyGenome
from quant_ecosystem.strategies.base.base_strategy import BaseStrategy
from quant_ecosystem.strategies.factory.strategy_factory import StrategyFactory


class AlphaFactory:

    def __init__(self, strategy_registry):

        self.registry = strategy_registry
        self.genome = StrategyGenome()
        self.factory = StrategyFactory(strategy_registry)

    def evolve(self):

        raw = self.registry.get_all()
        strategies = list(raw.values()) if isinstance(raw, dict) else list(raw or [])

        if not strategies:
            print("AlphaFactory: no strategies to evolve")
            return []

        evolved = []

        for strategy in strategies:
            if not (hasattr(strategy, "params") and hasattr(strategy, "id")):
                continue

            cls = type(strategy)
            if cls is BaseStrategy or cls.__name__.startswith("_DiscoveredStrategy"):
                continue

            child = self.factory.mutate_numeric_params(strategy)
            child.id = f"{strategy.id}_grid"
            child.name = f"{strategy.name} (grid)"
            self.registry.register(child)
            evolved.append(child)

        print(f"AlphaFactory: evolved {len(evolved)} strategies")

        return evolved