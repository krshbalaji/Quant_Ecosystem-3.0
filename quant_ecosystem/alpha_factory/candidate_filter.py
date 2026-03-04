"""Fast filter for Alpha Factory candidates."""

from __future__ import annotations

from typing import Dict, Iterable, List


class CandidateFilter:
    """Applies minimum Sharpe / max drawdown / min trade-count gates."""

    def __init__(self, min_sharpe: float = 1.0, max_drawdown: float = 15.0, min_trade_count: int = 30):
        self.min_sharpe = float(min_sharpe)
        self.max_drawdown = float(max_drawdown)
        self.min_trade_count = int(min_trade_count)

    def apply(self, evaluation_reports: Iterable[Dict]) -> List[Dict]:
        passed = []
        for row in list(evaluation_reports or []):
            sharpe = self._f(row.get("sharpe", 0.0))
            drawdown = self._f(row.get("drawdown", 0.0))
            trade_count = int(
                row.get("trade_count")
                or row.get("trades")
                or row.get("components", {}).get("shadow", {}).get("trades", 0)
                or 0
            )
            if sharpe < self.min_sharpe:
                continue
            if drawdown > self.max_drawdown:
                continue
            if trade_count < self.min_trade_count:
                continue
            passed.append(dict(row))
        return passed

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

