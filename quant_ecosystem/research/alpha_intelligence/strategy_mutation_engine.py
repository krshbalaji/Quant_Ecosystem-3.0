import random


class StrategyMutationEngine:

    def __init__(self):
        self.base_mutation = 0.18

    def mutate(self, genome, regime="neutral"):

        g = genome.copy()

        signal = g.get("signal_gene", {})

        strength = self.base_mutation

        if regime == "volatile":
            strength *= 1.6

        elif regime == "trending":
            strength *= 0.7

        if random.random() < strength:
            signal["threshold"] = max(
                0.001,
                signal.get("threshold", 0.02)
                + random.uniform(-0.01, 0.01),
            )

        if random.random() < strength:
            signal["lookback"] = max(
                6,
                int(signal.get("lookback", 20)
                    + random.randint(-5, 5))
            )

        g["signal_gene"] = signal

        return g