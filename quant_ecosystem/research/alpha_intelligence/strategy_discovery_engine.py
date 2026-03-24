import random
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:

    def __init__(self):

        self.symbol_family_bias = defaultdict(lambda: defaultdict(float))
        self.structural_graph_memory = defaultdict(int)

    # ==========================================================
    # MAIN DISCOVERY ENTRY
    # ==========================================================

    def discover(
        self,
        symbol,
        resolution,
        regime,
        alpha_density,
        cycle_memory,
    ):

        families = self._select_strategy_families(
            symbol,
            regime,
            alpha_density,
        )

        genomes = []

        for fam in families:

            mutation_vector = self._build_mutation_vector(
                fam,
                regime,
                alpha_density,
                cycle_memory,
            )

            g = self._synthesise_genome(
                symbol,
                resolution,
                fam,
                mutation_vector,
            )

            if not self._cluster_saturated(g):
                genomes.append(g)

        return genomes

    # ==========================================================
    # STRATEGY FAMILY MAPPER
    # ==========================================================

    def _select_strategy_families(
        self,
        symbol,
        regime,
        alpha_density,
    ):

        if regime == "TREND_STRONG":
            base = ["breakout", "pullback_trend", "ema_stack"]

        elif regime == "MEAN_REVERT":
            base = ["rsi_band", "bollinger_revert", "stoch_cycle"]

        elif regime == "VOL_EXPANSION":
            base = ["range_break", "atr_surge", "volatility_channel"]

        else:
            base = ["hybrid", "adaptive"]

        bias = self.symbol_family_bias[symbol]

        weighted = sorted(
            base,
            key=lambda f: bias[f]
        )

        if alpha_density < 2:
            return weighted[:3]

        return random.sample(weighted, min(3, len(weighted)))

    # ==========================================================
    # MUTATION VECTOR BUILDER
    # ==========================================================

    def _build_mutation_vector(
        self,
        family,
        regime,
        alpha_density,
        cycle_memory,
    ):

        intensity = 0.8 if alpha_density < 2 else 0.3

        if regime == "TREND_STRONG":
            horizon = random.choice(["medium", "long"])
        else:
            horizon = random.choice(["short", "medium"])

        lineage_push = cycle_memory.lineage_pressure()

        return {
            "family": family,
            "mutation_intensity": intensity,
            "holding_horizon": horizon,
            "lineage_push": lineage_push,
        }

    # ==========================================================
    # GENOME SYNTHESIS
    # ==========================================================

    def _synthesise_genome(
        self,
        symbol,
        resolution,
        family,
        vector,
    ):

        from quant_ecosystem.research.alpha_intelligence.genome import Genome

        g = Genome(
            symbol=symbol,
            resolution=resolution,
            family=family,
            parameters=self._randomise_parameters(vector),
            trained_regime=vector.get("regime"),
        )

        g.symbol = symbol
        g.resolution = resolution
        g.family = family
        g.parameters = self._randomise_parameters(vector)

        g.structural_signature = (
            family,
            vector["holding_horizon"],
            round(vector["mutation_intensity"], 2),
        )

        return g

    # ==========================================================
    # PARAMETER RANDOMISATION
    # ==========================================================

    def _randomise_parameters(self, vector):

        base = {}

        if vector["family"] == "breakout":
            base["lookback"] = random.randint(10, 60)

        if vector["family"] == "rsi_band":
            base["rsi_len"] = random.randint(5, 25)

        base["risk_factor"] = random.uniform(0.5, 2.0)

        return base

    # ==========================================================
    # CLUSTER SATURATION AVOIDANCE
    # ==========================================================

    def _cluster_saturated(self, genome):

        key = genome.structural_signature

        if self.structural_graph_memory[key] > 5:
            return True

        self.structural_graph_memory[key] += 1
        return False

    # ==========================================================
    # CONFIDENCE SUPPORT FUNCTIONS
    # ==========================================================

    def regime_alignment_score(self, genome, regime):

        if regime == "TREND_STRONG" and genome.family in [
            "breakout",
            "pullback_trend",
            "ema_stack",
        ]:
            return 1.0

        if regime == "MEAN_REVERT" and genome.family in [
            "rsi_band",
            "bollinger_revert",
        ]:
            return 1.0

        return 0.4

    def structural_novelty_score(self, genome):

        key = genome.structural_signature

        return 1.0 / (1 + self.structural_graph_memory[key])

    # ==========================================================
    # FALLBACK RANDOM STREAM
    # ==========================================================

    def random_genomes(self, symbol, resolution):

        logger.info("[discovery] generating fallback genomes")

        return [
            self._synthesise_genome(
                symbol,
                resolution,
                random.choice(["hybrid", "adaptive"]),
                {
                    "family": "hybrid",
                    "mutation_intensity": 1.0,
                    "holding_horizon": "short",
                    "lineage_push": 0,
                },
            )
            for _ in range(3)
        ]