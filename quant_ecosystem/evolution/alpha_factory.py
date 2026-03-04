from quant_ecosystem.evolution.strategy_genome import StrategyGenome


class AlphaFactory:

    def __init__(self, strategy_registry):

        self.registry = strategy_registry
        self.genome = StrategyGenome()

    def evolve(self):

        strategies = self.registry.get_all()

        if not strategies:
            print("AlphaFactory: no strategies to evolve")
            return []

        evolved = []

        for strategy in strategies:

            mutated = self.genome.mutate(strategy)

            self.registry.register(mutated)

            evolved.append(mutated)

        print(f"AlphaFactory: evolved {len(evolved)} strategies")

        return evolved