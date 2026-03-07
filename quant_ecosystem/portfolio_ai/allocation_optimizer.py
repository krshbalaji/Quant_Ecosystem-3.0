"""Allocation optimizer for Portfolio AI."""

from __future__ import annotations

from typing import Dict, Iterable, List

from quant_ecosystem.portfolio_ai.correlation_analyzer import CorrelationAnalyzer


class AllocationOptimizer:
    """Computes risk-adjusted optimized allocation weights."""

    def __init__(self, correlation_analyzer: CorrelationAnalyzer | None = None, **kwargs):
        self.correlation_analyzer = correlation_analyzer or CorrelationAnalyzer(threshold=0.75)

    def optimize(self, strategy_rows: Iterable[Dict], capital_pct: float = 100.0) -> Dict:
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        if not rows:
            return {"weights": {}, "correlation_clusters": [], "scores": {}}

        corr = self.correlation_analyzer.analyze(rows)
        matrix = corr["matrix"]
        clusters = corr["clusters"]
        raw_scores = {}
        for row in rows:
            sid = str(row.get("id"))
            raw_scores[sid] = self._score(row, matrix)

        total = sum(max(0.0, s) for s in raw_scores.values())
        if total <= 1e-9:
            equal = float(capital_pct) / len(rows)
            weights = {str(row.get("id")): round(equal, 6) for row in rows}
        else:
            weights = {
                sid: round((max(0.0, raw_scores[sid]) / total) * float(capital_pct), 6)
                for sid in raw_scores
            }

        return {"weights": weights, "correlation_clusters": clusters, "scores": raw_scores}

    def _score(self, row: Dict, correlation_matrix: Dict[str, Dict[str, float]]) -> float:
        sid = str(row.get("id"))
        sharpe = self._metric(row, "sharpe")
        expectancy = self._metric(row, "expectancy")
        profit_factor = self._metric(row, "profit_factor")
        drawdown = self._metric(row, "max_dd", "max_drawdown")
        volatility = self._volatility(row)
        corr_penalty = self.correlation_analyzer.correlation_penalty(sid, correlation_matrix)

        # Mean-variance and Sharpe-aware score.
        sharpe_term = max(-2.0, min(4.0, sharpe)) + 2.0
        pf_term = max(0.0, min(3.0, profit_factor))
        exp_term = max(-1.0, min(1.0, expectancy)) + 1.0
        risk_term = 1.0 / max(0.01, volatility + (drawdown / 100.0))
        corr_term = max(0.05, 1.0 - corr_penalty)

        score = (0.35 * sharpe_term) + (0.20 * pf_term) + (0.20 * exp_term) + (0.25 * risk_term)
        return round(max(0.0, score * corr_term), 8)

    def _volatility(self, row: Dict) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        returns = metrics.get("returns", row.get("returns", []))
        vals: List[float] = []
        for value in returns or []:
            try:
                vals.append(float(value))
            except (TypeError, ValueError):
                continue
        if len(vals) < 2:
            fallback = metrics.get("volatility", row.get("volatility", 0.2))
            try:
                return max(0.01, abs(float(fallback)))
            except (TypeError, ValueError):
                return 0.2
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
        return max(0.01, var ** 0.5)

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

    def _float(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

