"""
Capital Intelligence Engine
===========================

Responsible for:
- Capital allocation intelligence
- Portfolio capital efficiency
- Strategy capital scoring
- Risk adjusted allocation

Future Extensions
-----------------
Kelly optimization
Dynamic capital rotation
Strategy capital reinforcement learning
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CapitalIntelligenceEngine:

    def __init__(self, config: Any, **kwargs):
        self.config = config
        self.total_capital = getattr(config, "initial_capital", 1000000)

        logger.info("CapitalIntelligenceEngine initialized.")

    def evaluate_strategy_capital(self, strategy_metrics: Dict) -> float:
        """
        Calculate capital allocation weight for strategy.
        """

        if not strategy_metrics:
            return 0.0

        sharpe = strategy_metrics.get("sharpe", 0)
        winrate = strategy_metrics.get("winrate", 0)
        drawdown = strategy_metrics.get("max_drawdown", 1)

        score = (sharpe * 0.5) + (winrate * 0.3) - (drawdown * 0.2)

        return max(score, 0)

    def regime_multiplier(self, regime: str) -> float:
        key = str(regime or "RANGE").upper()
        if key in {"TREND", "TRENDING_BULL", "TRENDING_BEAR"}:
            return 1.5
        if key in {"RANGE", "MEAN_REVERSION"}:
            return 0.5
        if key in {"LOW_VOL", "LOW_VOLATILITY"}:
            return 0.3
        return 1.0

    def allocate(self, strategies: Dict[str, Dict]) -> Dict[str, float]:
        """
        Allocate capital across strategies.
        """

        scores = {}
        total_score = 0

        for name, metrics in strategies.items():
            score = self.evaluate_strategy_capital(metrics)
            scores[name] = score
            total_score += score

        if total_score == 0:
            return {}

        allocation = {}

        for name, score in scores.items():
            weight = score / total_score
            allocation[name] = weight * self.total_capital

        return allocation

    def allocate_dynamic(self, strategy_id: str, base_capital: float, confidence: float, regime: str, strategy_metrics: Dict | None = None) -> float:
        regime_multiplier = self.regime_multiplier(regime)
        performance_weight = 1.0
        if strategy_metrics:
            performance_weight += min(max(self.evaluate_strategy_capital(strategy_metrics), 0.0), 1.0)
        capital = float(base_capital) * float(confidence) * regime_multiplier * performance_weight
        return round(max(capital, 0.0), 2)

    def capital_snapshot(self) -> Dict:
        """
        Return capital state snapshot.
        """

        return {
            "total_capital": self.total_capital
        }
