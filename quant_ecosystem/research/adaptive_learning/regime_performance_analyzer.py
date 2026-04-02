"""Regime-specific strategy performance analyzer."""

from __future__ import annotations

from typing import Dict, List


class RegimePerformanceAnalyzer:
    """Analyzes best/weak regimes for each strategy."""

    def analyze(self, rows: List[Dict]) -> Dict:
        grouped: Dict[str, List[Dict]] = {}
        for row in rows or []:
            sid = str(row.get("strategy_id", "")).strip()
            if not sid:
                continue
            grouped.setdefault(sid, []).append(dict(row))

        out = {"strategies": {}}
        for sid, values in grouped.items():
            ranked = sorted(values, key=lambda x: self._score(x), reverse=True)
            best = ranked[0] if ranked else {}
            weak = ranked[-1] if ranked else {}
            out["strategies"][sid] = {
                "best_regime": best.get("regime", "UNKNOWN"),
                "weak_regime": weak.get("regime", "UNKNOWN"),
                "best_metrics": {
                    "avg_pnl": best.get("avg_pnl", 0.0),
                    "win_rate": best.get("win_rate", 0.0),
                    "sharpe": best.get("sharpe", 0.0),
                },
                "weak_metrics": {
                    "avg_pnl": weak.get("avg_pnl", 0.0),
                    "win_rate": weak.get("win_rate", 0.0),
                    "sharpe": weak.get("sharpe", 0.0),
                },
                "regime_scores": {row.get("regime", "UNKNOWN"): round(self._score(row), 6) for row in values},
            }
        return out

    def _score(self, row: Dict) -> float:
        sharpe = float(row.get("sharpe", 0.0))
        win_rate = float(row.get("win_rate", 0.0)) / 100.0
        avg_pnl = float(row.get("avg_pnl", 0.0))
        trades = max(1, int(row.get("trades", 1)))
        confidence = min(1.0, trades / 200.0)
        return (0.45 * sharpe) + (0.30 * win_rate) + (0.25 * avg_pnl) * confidence

