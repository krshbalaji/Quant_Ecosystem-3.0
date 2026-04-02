"""Risk-adjusted scoring and proportional allocation."""

from __future__ import annotations

from typing import Dict, Iterable, List


class RiskAdjustedAllocator:
    """Allocates strategy capital proportionally to risk-adjusted scores.

    Score formula:
        score = sharpe * win_rate / drawdown
    """

    def __init__(self, min_drawdown_denominator: float = 0.5, **kwargs):
        self.min_drawdown_denominator = float(max(0.1, min_drawdown_denominator))

    def compute_score(self, strategy_row: Dict) -> float:
        metrics = strategy_row.get("metrics", strategy_row)
        sharpe = float(metrics.get("sharpe", strategy_row.get("sharpe", 0.0)))
        win_rate = float(metrics.get("win_rate", strategy_row.get("win_rate", 0.0)))
        drawdown = float(
            metrics.get(
                "max_dd",
                metrics.get("max_drawdown", strategy_row.get("max_drawdown", 0.0)),
            )
        )
        dd_den = max(abs(drawdown), self.min_drawdown_denominator)
        return (sharpe * max(win_rate, 0.0)) / dd_den

    def allocate(self, strategies: Iterable[Dict], capital_available_pct: float = 100.0) -> Dict[str, float]:
        rows: List[Dict] = []
        for row in strategies:
            item = dict(row)
            score = self.compute_score(item)
            item["risk_adjusted_score"] = score
            rows.append(item)

        positive = [row for row in rows if float(row.get("risk_adjusted_score", 0.0)) > 0]
        if not positive:
            return {}

        total_score = sum(float(row["risk_adjusted_score"]) for row in positive)
        cap = max(0.0, min(100.0, float(capital_available_pct)))
        out: Dict[str, float] = {}
        for row in positive:
            sid = str(row.get("id", "")).strip()
            if not sid:
                continue
            weight = float(row["risk_adjusted_score"]) / total_score
            out[sid] = round(weight * cap, 4)
        return out

