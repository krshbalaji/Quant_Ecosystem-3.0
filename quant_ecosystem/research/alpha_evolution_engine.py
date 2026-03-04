import random
import time


class AlphaEvolutionEngine:

    def __init__(
        self,
        strategy_registry,
        mutation_engine,
        crossover_engine,
        evaluation_engine,
        interval=600,
    ):

        self.registry = strategy_registry
        self.mutation = mutation_engine
        self.crossover = crossover_engine
        self.evaluator = evaluation_engine

        self.interval = interval
        self.last_run = 0

    def start(self):

        print("Alpha Evolution Engine started.")

    def evolve(self):

        now = time.time()

        if now - self.last_run < self.interval:
            return

        self.last_run = now

        parents = self._select_parents()

        if not parents:
            return

        children = []

        for _ in range(5):

            if random.random() < 0.5:
                child = self.mutation.mutate(parents[0])

            else:
                child = self.crossover.cross(parents[0], parents[1])

            children.append(child)

        for strategy in children:

            result = self.evaluator.evaluate(strategy)

            if result["score"] > 1.2:

                self.registry.register_strategy(strategy)

                print(
                    "AlphaEvolution: new strategy promoted",
                    strategy["name"],
                )

    def _select_parents(self):

        strategies = self.registry.get_top_strategies(10)

        if len(strategies) < 2:
            return None

        return random.sample(strategies, 2)