import random
import copy


class StrategyMutationEngine:

    def __init__(self):

        self.mutation_rate = 0.25

    # -----------------------------------------------------

    def mutate_batch(self, genomes):

        mutated = []

        for g in genomes:

            if random.random() < self.mutation_rate:

                mutated.append(self._mutate(copy.deepcopy(g)))

        return mutated

    # -----------------------------------------------------

    def _mutate(self, genome):

        mode = random.choice([

            "threshold",
            "lookback",
            "indicator_flip",
            "risk",
            "regime_shift"
        ])

        if mode == "threshold":

            genome["signal_gene"]["threshold"] *= random.uniform(0.7, 1.3)

        elif mode == "lookback":

            genome["signal_gene"]["lookback"] = max(
                5,
                int(genome["signal_gene"]["lookback"] * random.uniform(0.6, 1.4))
            )

        elif mode == "indicator_flip":

            pool = [
                "momentum",
                "mean_reversion",
                "breakout",
                "ma_cross",
                "rsi",
                "volatility_breakout"
            ]

            genome["signal_gene"]["indicator"] = random.choice(pool)

        elif mode == "risk":

            genome["risk_gene"]["stop_loss"] *= random.uniform(0.8, 1.4)
            genome["risk_gene"]["take_profit"] *= random.uniform(0.8, 1.6)

        elif mode == "regime_shift":

            genome["meta"]["regime_target"] = random.choice(
                ["trend", "mean", "volatile"]
            )

        genome["meta"]["mutated"] = True

        return genome