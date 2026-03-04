"""Portfolio state tracking for dynamic optimizer."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List


class PortfolioStateManager:
    """Tracks evolving portfolio state and risk metrics."""

    def __init__(self):
        self._history: List[Dict] = []
        self._latest: Dict = {}

    def update(
        self,
        allocations: Dict[str, float],
        strategy_rows: Iterable[Dict],
        risk_contributions: Dict[str, float] | None = None,
        correlation_clusters: List[List[str]] | None = None,
    ) -> Dict:
        rows = [dict(row) for row in strategy_rows if row.get("id")]
        state = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "strategy_weights": dict(allocations),
            "portfolio_volatility": round(self._portfolio_vol(allocations, rows), 6),
            "portfolio_drawdown": round(self._portfolio_drawdown(rows), 6),
            "risk_exposure": round(sum(max(0.0, float(v)) for v in allocations.values()), 6),
            "risk_contributions": dict(risk_contributions or {}),
            "correlation_clusters": list(correlation_clusters or []),
        }
        self._latest = state
        self._history.append(state)
        if len(self._history) > 500:
            self._history = self._history[-500:]
        return state

    def latest(self) -> Dict:
        return dict(self._latest)

    def history(self) -> List[Dict]:
        return list(self._history)

    def _portfolio_vol(self, allocations: Dict[str, float], rows: List[Dict]) -> float:
        by_id = {str(row.get("id")): row for row in rows}
        variance = 0.0
        for sid, w_pct in allocations.items():
            row = by_id.get(str(sid), {})
            vol = self._vol(row)
            w = float(w_pct) / 100.0
            variance += (w * vol) ** 2
        return variance ** 0.5

    def _portfolio_drawdown(self, rows: List[Dict]) -> float:
        drawdowns = []
        for row in rows:
            metrics = row.get("metrics", row.get("raw_metrics", {}))
            dd = metrics.get("max_dd", metrics.get("max_drawdown", row.get("max_drawdown", 0.0)))
            try:
                drawdowns.append(float(dd))
            except (TypeError, ValueError):
                continue
        if not drawdowns:
            return 0.0
        return sum(drawdowns) / len(drawdowns)

    def _vol(self, row: Dict) -> float:
        metrics = row.get("metrics", row.get("raw_metrics", {}))
        returns = metrics.get("returns", row.get("returns", []))
        vals = []
        for r in returns or []:
            try:
                vals.append(float(r))
            except (TypeError, ValueError):
                continue
        if len(vals) < 2:
            try:
                return max(0.01, abs(float(metrics.get("volatility", row.get("volatility", 0.2)))))
            except (TypeError, ValueError):
                return 0.2
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
        return max(0.01, var ** 0.5)

