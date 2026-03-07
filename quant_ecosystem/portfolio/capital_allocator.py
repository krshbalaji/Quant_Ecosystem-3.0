from __future__ import annotations

from typing import Dict, List, Tuple


class CapitalAllocator:
    """
    Simple institutional-style capital allocation engine.

    Weights strategies based on risk-adjusted performance metrics
    (Sharpe, drawdown, win-rate, profit factor).
    """

    def __init__(self, max_strategies: int = 10, **kwargs):
        self.max_strategies = max_strategies

    def allocate(self, metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Compute allocation weights from a mapping:
        strategy_id -> {sharpe, drawdown, win_rate, profit_factor, ...}
        """
        scored: List[Tuple[str, float]] = []
        for sid, row in metrics.items():
            sharpe = float(row.get("sharpe", 0.0))
            drawdown = float(row.get("drawdown", 0.0))
            win_rate = float(row.get("win_rate", 0.0))
            profit_factor = float(row.get("profit_factor", 0.0))

            dd_penalty = 1.0 + max(0.0, drawdown / 20.0)
            raw_score = sharpe * profit_factor * (win_rate / 50.0)
            score = raw_score / dd_penalty
            if score <= 0:
                continue
            scored.append((sid, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[: self.max_strategies]
        total = sum(score for _, score in top)
        if total <= 0:
            return {}
        return {sid: score / total for sid, score in top}

class CapitalAllocator:

    def allocate(self, strategies):

        total_score = sum([s["score"] for s in strategies])

        allocation = {}

        for s in strategies:

            weight = s["score"] / total_score

            allocation[s["name"]] = round(weight, 4)

        return allocation