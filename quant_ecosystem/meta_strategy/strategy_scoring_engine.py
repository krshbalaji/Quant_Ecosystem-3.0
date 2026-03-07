"""Dynamic scoring engine for strategy ecosystem governance."""

from __future__ import annotations

from math import sqrt
from typing import Dict, Iterable, List


class StrategyScoringEngine:
    """Computes dynamic strategy score with stability and recency signals."""

    def __init__(
        self,
        weight_sharpe: float = 0.30,
        weight_profit_factor: float = 0.20,
        weight_expectancy: float = 0.20,
        weight_win_rate: float = 0.10,
        weight_stability: float = 0.10,
        weight_drawdown_penalty: float = 0.10, **kwargs
    ):
        self.weight_sharpe = float(weight_sharpe)
        self.weight_profit_factor = float(weight_profit_factor)
        self.weight_expectancy = float(weight_expectancy)
        self.weight_win_rate = float(weight_win_rate)
        self.weight_stability = float(weight_stability)
        self.weight_drawdown_penalty = float(weight_drawdown_penalty)

    def score(self, strategy_row: Dict) -> float:
        """Returns a dynamic meta score for a single strategy row."""
        sharpe = self._metric(strategy_row, "sharpe")
        profit_factor = self._metric(strategy_row, "profit_factor")
        expectancy = self._metric(strategy_row, "expectancy")
        win_rate = self._metric(strategy_row, "win_rate")
        drawdown = self._metric(strategy_row, "max_dd", "max_drawdown")
        stability = self._stability(strategy_row)
        recent = self._recent_performance(strategy_row)

        sharpe_score = self._norm(sharpe, -2.0, 3.0)
        pf_score = self._norm(profit_factor, 0.5, 3.0)
        expectancy_score = self._norm(expectancy, -1.0, 1.0)
        win_score = self._norm(win_rate, 0.0, 100.0)
        stability_score = self._norm(stability, 0.0, 1.0)
        drawdown_penalty = self._norm(drawdown, 0.0, 30.0)
        recent_score = self._norm(recent, -1.0, 1.0)

        base = (
            self.weight_sharpe * sharpe_score
            + self.weight_profit_factor * pf_score
            + self.weight_expectancy * expectancy_score
            + self.weight_win_rate * win_score
            + self.weight_stability * stability_score
            - self.weight_drawdown_penalty * drawdown_penalty
        )
        # Recency overlay: +/- 10% of base score, bounded.
        adjusted = base * (1.0 + (recent_score - 0.5) * 0.2)
        return round(max(0.0, adjusted), 6)

    def score_batch(self, strategy_rows: Iterable[Dict]) -> List[Dict]:
        """Scores and returns sorted strategy rows (best first)."""
        out = []
        for row in strategy_rows:
            item = dict(row)
            item["meta_score"] = self.score(item)
            out.append(item)
        out.sort(key=lambda row: float(row.get("meta_score", 0.0)), reverse=True)
        return out

    def _metric(self, row: Dict, primary: str, fallback: str | None = None) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        if primary in metrics:
            return self._float(metrics.get(primary))
        if primary in row:
            return self._float(row.get(primary))
        if fallback:
            if fallback in metrics:
                return self._float(metrics.get(fallback))
            if fallback in row:
                return self._float(row.get(fallback))
        return 0.0

    def _stability(self, row: Dict) -> float:
        returns = self._returns(row)
        if len(returns) < 10:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((value - mean) ** 2 for value in returns) / max(1, len(returns) - 1)
        std = sqrt(max(1e-12, variance))
        # Convert coefficient-of-variation like signal to [0,1], higher is more stable.
        ratio = abs(mean) / std if std > 0 else 0.0
        return max(0.0, min(1.0, ratio))

    def _recent_performance(self, row: Dict) -> float:
        returns = self._returns(row)
        if not returns:
            return 0.0
        tail = returns[-20:]
        return sum(tail) / len(tail)

    def _returns(self, row: Dict) -> List[float]:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        src = metrics.get("returns", row.get("returns", []))
        out = []
        for item in src or []:
            try:
                out.append(float(item))
            except (TypeError, ValueError):
                continue
        return out[-200:]

    def _float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _norm(self, value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0
        clipped = min(max(value, low), high)
        return (clipped - low) / (high - low)

