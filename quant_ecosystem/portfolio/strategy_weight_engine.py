import logging

logger = logging.getLogger(__name__)


class StrategyWeightEngine:

    def __init__(self):

        self.min_weight = 0.05
        self.max_weight = 0.40

        logger.info("StrategyWeightEngine initialized")

    def compute_weights(self, strategies, regime):

        weights = {}

        for s in strategies:

            sharpe = s.get("sharpe", 0)
            drawdown = abs(s.get("max_dd", 1))
            stability = s.get("stability", 0.5)

            regime_bonus = self._regime_score(s, regime)

            score = (
                sharpe * 0.6 +
                stability * 0.3 +
                regime_bonus * 0.4
            ) / (1 + drawdown)

            weights[s["name"]] = max(self.min_weight, min(self.max_weight, score))

        return self._normalize(weights)

    def _regime_score(self, strategy, regime):

        supported = strategy.get("regimes", [])

        if regime in supported:
            return 1.0

        return 0.2

    def _normalize(self, weights):

        total = sum(weights.values())

        if total == 0:
            return weights

        for k in weights:
            weights[k] /= total

        return weights