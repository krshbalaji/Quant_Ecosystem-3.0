import logging
import random
from collections import defaultdict

logger = logging.getLogger(__name__)


class PromotionProbabilityEngine:

    def __init__(
        self,
        regime_memory,
        cycle_memory,
        capital_governor=None,
    ):
        self.regime_memory = regime_memory
        self.cycle_memory = cycle_memory
        self.capital_governor = capital_governor

        self.symbol_promotions = defaultdict(int)
        self.family_crowding = defaultdict(int)

    # ==========================================================
    # MAIN ENTRY
    # ==========================================================

    def select(self, evaluated_batch):

        scored = []

        for g in evaluated_batch:

            score = self._promotion_score(g)

            g.promotion_score = score

            if self._promotion_draw(score):
                scored.append(g)

        diversified = self._apply_symbol_pressure(scored)

        logger.info(
            f"[promotion] promoted {len(diversified)} / {len(evaluated_batch)}"
        )

        return diversified

    # ==========================================================
    # PROMOTION SCORE
    # ==========================================================

    def _promotion_score(self, g):

        fitness = getattr(g, "fitness_score", 0.5)
        confidence = getattr(g, "alpha_confidence", 0.5)

        regime_prob = self._regime_persistence_probability(g)

        capital_eff = self._capital_efficiency_score(g)

        crowd_penalty = self._crowding_penalty(g)

        decay_penalty = self._decay_probability(g)

        diversification = self._diversification_bonus(g)

        score = (
            fitness
            * confidence
            * regime_prob
            * capital_eff
            * diversification
            * (1 - crowd_penalty)
            * (1 - decay_penalty)
        )

        return max(0.0, min(1.0, score))

    # ==========================================================
    # REGIME PERSISTENCE
    # ==========================================================

    def _regime_persistence_probability(self, g):

        regime = self.regime_memory.get_current_regime(
            g.symbol,
            g.resolution,
        )

        stability = self.regime_memory.regime_stability(
            g.symbol,
            g.resolution,
        )

        return 0.5 + 0.5 * stability

    # ==========================================================
    # CAPITAL EFFICIENCY
    # ==========================================================

    def _capital_efficiency_score(self, g):

        sharpe = getattr(g, "sharpe", 1.0)
        dd = getattr(g, "max_dd", 0.2)

        eff = sharpe / (1 + dd * 3)

        return max(0.2, min(1.2, eff))

    # ==========================================================
    # CROWDING
    # ==========================================================

    def _crowding_penalty(self, g):

        key = (g.family, g.resolution)

        c = self.family_crowding[key]

        penalty = min(0.6, c * 0.08)

        self.family_crowding[key] += 1

        return penalty

    # ==========================================================
    # DECAY MODEL
    # ==========================================================

    def _decay_probability(self, g):

        age_pressure = self.cycle_memory.alpha_decay_pressure(g)

        return min(0.7, age_pressure)

    # ==========================================================
    # DIVERSIFICATION BONUS
    # ==========================================================

    def _diversification_bonus(self, g):

        promoted_count = self.symbol_promotions[g.symbol]

        bonus = 1.0 / (1 + promoted_count * 0.4)

        return max(0.4, bonus)

    # ==========================================================
    # STOCHASTIC PROMOTION GATE
    # ==========================================================

    def _promotion_draw(self, score):

        threshold = random.uniform(0.3, 0.9)

        return score > threshold

    # ==========================================================
    # FINAL SYMBOL PRESSURE
    # ==========================================================

    def _apply_symbol_pressure(self, promoted):

        final = []

        for g in promoted:

            if self.symbol_promotions[g.symbol] > 5:
                continue

            self.symbol_promotions[g.symbol] += 1
            final.append(g)

        return final