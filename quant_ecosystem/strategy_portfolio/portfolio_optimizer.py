"""Portfolio optimization for strategy-family diversification.

This module is additive and optional. It produces an optimized candidate list
for strategy activation but does not place trades or bypass risk controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Iterable, List, Tuple


@dataclass
class OptimizerWeights:
    """Weight model used by the optimizer score."""

    sharpe: float = 0.35
    expectancy: float = 0.30
    drawdown: float = 0.20
    correlation: float = 0.15


class PortfolioOptimizer:
    """Selects low-correlation, high-quality strategies for a portfolio."""

    def __init__(
        self,
        max_strategies: int = 5,
        correlation_threshold: float = 0.7,
        weights: OptimizerWeights | None = None,
    ):
        self.max_strategies = max(1, int(max_strategies))
        self.correlation_threshold = max(0.0, min(0.99, float(correlation_threshold)))
        self.weights = weights or OptimizerWeights()

    def optimize(
        self,
        strategy_rows: Iterable[Dict],
        max_strategies: int | None = None,
        correlation_threshold: float | None = None,
    ) -> List[Dict]:
        """Returns an optimized subset based on score and diversification."""
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        if not rows:
            return []

        limit = self.max_strategies if max_strategies is None else max(1, int(max_strategies))
        corr_limit = self.correlation_threshold if correlation_threshold is None else max(
            0.0, min(0.99, float(correlation_threshold))
        )

        scored = []
        for row in rows:
            item = dict(row)
            item["portfolio_score"] = round(self._score(item), 6)
            scored.append(item)
        scored.sort(key=lambda row: float(row.get("portfolio_score", 0.0)), reverse=True)

        selected: List[Dict] = []
        for candidate in scored:
            if len(selected) >= limit:
                break
            if self._violates_correlation(candidate, selected, corr_limit):
                continue
            selected.append(candidate)

        if not selected:
            return scored[:limit]
        return selected

    def _score(self, row: Dict) -> float:
        sharpe = self._get_metric(row, "sharpe")
        expectancy = self._get_metric(row, "expectancy")
        drawdown = self._get_metric(row, "max_dd", "max_drawdown")
        corr_penalty = self._get_metric(row, "correlation_penalty")

        sharpe_score = self._norm(sharpe, 0.0, 3.0)
        expectancy_score = self._norm(expectancy, -1.0, 1.0)
        drawdown_score = 1.0 - self._norm(drawdown, 0.0, 40.0)
        corr_score = 1.0 - self._norm(corr_penalty, 0.0, 1.0)

        return (
            self.weights.sharpe * sharpe_score
            + self.weights.expectancy * expectancy_score
            + self.weights.drawdown * drawdown_score
            + self.weights.correlation * corr_score
        )

    def _violates_correlation(self, candidate: Dict, selected: List[Dict], threshold: float) -> bool:
        for active in selected:
            corr = self._pair_correlation(candidate, active)
            if corr > threshold:
                return True
        return False

    def _pair_correlation(self, left: Dict, right: Dict) -> float:
        # Prefer declared correlation cluster signal when available.
        cluster_l = str(left.get("correlation_cluster", "")).strip()
        cluster_r = str(right.get("correlation_cluster", "")).strip()
        if cluster_l and cluster_r and cluster_l == cluster_r:
            return 1.0

        returns_l = self._returns(left)
        returns_r = self._returns(right)
        if len(returns_l) >= 10 and len(returns_r) >= 10:
            return abs(self._pearson(returns_l, returns_r))

        # Conservative fallback by category/family similarity.
        fam_l = str(left.get("family", left.get("category", ""))).strip().lower()
        fam_r = str(right.get("family", right.get("category", ""))).strip().lower()
        if fam_l and fam_r and fam_l == fam_r:
            return 0.8
        return 0.0

    def _returns(self, row: Dict) -> List[float]:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        data = metrics.get("returns", row.get("returns", []))
        out = []
        for value in data or []:
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
        return out[-120:]

    def _pearson(self, left: List[float], right: List[float]) -> float:
        n = min(len(left), len(right))
        if n < 2:
            return 0.0
        x = left[-n:]
        y = right[-n:]
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = 0.0
        den_x = 0.0
        den_y = 0.0
        for i in range(n):
            dx = x[i] - mean_x
            dy = y[i] - mean_y
            num += dx * dy
            den_x += dx * dx
            den_y += dy * dy
        den = sqrt(den_x * den_y)
        if den <= 1e-12:
            return 0.0
        return num / den

    def _get_metric(self, row: Dict, primary: str, fallback: str | None = None) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        if primary in metrics:
            return self._safe_float(metrics.get(primary))
        if primary in row:
            return self._safe_float(row.get(primary))
        if fallback:
            if fallback in metrics:
                return self._safe_float(metrics.get(fallback))
            if fallback in row:
                return self._safe_float(row.get(fallback))
        return 0.0

    def _safe_float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _norm(self, value: float, low: float, high: float) -> float:
        if high <= low:
            return 0.0
        clipped = min(max(value, low), high)
        return (clipped - low) / (high - low)
