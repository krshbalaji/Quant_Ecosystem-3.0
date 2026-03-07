import random
from typing import List
from quant_ecosystem.evolution.alpha_genome_engine import AlphaGenomeEngine

import logging

logger = logging.getLogger(__name__)


class AlphaEvolutionEngine:

    def __init__(self, config=None, genome_engine=None, **kwargs):
        self.config = config
        self.genome_engine = genome_engine

        logger.info("AlphaEvolutionEngine initialized")

    def evolve(self, strategies=None):

        logger.info("Running alpha evolution")

        return strategies

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