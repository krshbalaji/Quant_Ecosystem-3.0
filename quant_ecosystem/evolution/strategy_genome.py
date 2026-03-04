import random


class StrategyGenome:

    def mutate(self, strategy):

        mutated = strategy.copy()

        params = mutated.get("parameters", {})

        for key in params:

            change = random.uniform(-0.2, 0.2)

            params[key] = max(0.01, params[key] * (1 + change))

        mutated["parameters"] = params

        return mutated