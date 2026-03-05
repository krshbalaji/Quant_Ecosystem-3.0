import random
from typing import List
from quant_ecosystem.evolution.alpha_genome_engine import AlphaGenomeEngine

class AlphaEvolutionEngine:
    """
    Strategy mutation and evolution engine.
    Creates new strategies from top performers.
    """

    def __init__(self, strategy_registry):
        self.strategy_registry = strategy_registry
        self.genome_engine = AlphaGenomeEngine()
    
    def evolve(self):

        strategies = self._get_strategies()

        if not strategies:
            print("AlphaEvolution: no strategies available")
            return []

        parents = sorted(
            strategies,
            key=lambda s: getattr(s, "score", 0),
            reverse=True
        )[:3]

        children = []

        for p in parents:
            child = self._mutate(p)
            children.append(child)

        print(f"AlphaEvolution: created {len(children)} new strategies")

        return children
    
    def generate_initial_populations(self):
        population = self.genome_engine.generate_population(1000)
        return population
        
    def _mutate(self, strategy):

        params = getattr(strategy, "params", {}).copy()

        for k in params:
            if isinstance(params[k], (int, float)):
                params[k] *= random.uniform(0.9, 1.1)

        new_strategy = type(strategy)()

        new_strategy.params = params
        new_strategy.name = strategy.name + "_mut"

        return new_strategy

    def _get_strategies(self):

        if hasattr(self.strategy_registry, "get_all"):
            return self.strategy_registry.get_all()

        if hasattr(self.strategy_registry, "strategies"):
            return list(self.strategy_registry.strategies.values())

        return []

    def run(self):
        return self.evolve()