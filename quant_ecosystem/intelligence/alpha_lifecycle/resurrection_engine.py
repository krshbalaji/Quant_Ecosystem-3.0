class ResurrectionEngine:

    def should_resurrect(self, genome, regime_memory):

        trained = getattr(genome, "trained_regime", None)

        current = regime_memory.get_current_regime(
            genome.symbol,
            genome.resolution,
        )

        return trained == current