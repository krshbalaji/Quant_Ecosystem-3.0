import random
import copy
import time


class StrategyMutationEngine:
    """
    Institutional Regime Aware Mutation Engine
    """

    def __init__(self, regime_memory=None):
        self.regime_memory = regime_memory

        print("🧬 StrategyMutationEngine initialized (Regime Aware)")

    # -----------------------------------------------------

    def mutate(self, genomes, n_offspring=15):

        offspring = []

        for _ in range(n_offspring):

            parent = random.choice(genomes)

            child = copy.deepcopy(parent)

            self._mutate_gene(child)

            child["genome_id"] = f"mut_{int(time.time()*1000)}"

            offspring.append(child)

        return offspring

    # -----------------------------------------------------

    def _mutate_gene(self, genome):

        gene = genome.get("signal_gene", {})

        if not gene:
            return

        mutation_type = random.choice([
            "lookback",
            "threshold",
            "indicator_shift"
        ])

        if mutation_type == "lookback":

            gene["lookback"] = max(
                5,
                gene.get("lookback", 20) + random.randint(-10, 10)
            )

        elif mutation_type == "threshold":

            gene["threshold"] = max(
                0.001,
                gene.get("threshold", 0.5) + random.uniform(-0.3, 0.3)
            )

        elif mutation_type == "indicator_shift":

            regime_hint = self._regime_hint()

            if regime_hint == "TRENDING":
                gene["indicator"] = random.choice(["momentum", "breakout"])

            elif regime_hint == "MEAN_REVERT":
                gene["indicator"] = "mean_reversion"

            elif regime_hint == "VOLATILE":
                gene["indicator"] = "volatility_breakout"

    # -----------------------------------------------------

    def _regime_hint(self):

        if self.regime_memory is None:
            return "UNKNOWN"

        try:
            return self.regime_memory.last_successful_regime()
        except Exception:
            return "UNKNOWN"