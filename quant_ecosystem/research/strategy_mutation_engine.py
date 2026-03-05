import random
import copy
import logging

logger = logging.getLogger(__name__)


class StrategyMutationEngine:
    """
    Mutates strategies to create new alpha variations.
    Part of the Alpha Genome layer.
    """

    def __init__(self):
        logger.info("StrategyMutationEngine initialized")

    def mutate(self, strategy):
        """
        Create mutated variations of a strategy.
        """

        mutated = copy.deepcopy(strategy)

        if "parameters" not in mutated:
            return mutated

        for param in mutated["parameters"]:

            value = mutated["parameters"][param]

            if isinstance(value, (int, float)):
                mutation = random.uniform(-0.2, 0.2)
                mutated["parameters"][param] = value * (1 + mutation)

        return mutated

    def generate_population(self, base_strategy, size=20):
        """
        Create multiple mutated strategies.
        """

        population = []

        for _ in range(size):
            population.append(self.mutate(base_strategy))

        return population