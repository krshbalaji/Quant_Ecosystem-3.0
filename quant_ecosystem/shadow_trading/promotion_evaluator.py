"""Promotion evaluator for shadow-to-paper/live transitions."""

from __future__ import annotations

from typing import Dict, List


class PromotionEvaluator:
    """Evaluates shadow strategy metrics for promotion events."""

    def __init__(
        self,
        min_sharpe: float = 1.2,
        max_drawdown: float = 5.0,
        min_trades: int = 50,
    ):
        self.min_sharpe = float(min_sharpe)
        self.max_drawdown = float(max_drawdown)
        self.min_trades = int(min_trades)

    def evaluate(self, metrics_by_strategy: Dict[str, Dict]) -> List[Dict]:
        events = []
        for sid, m in (metrics_by_strategy or {}).items():
            sharpe = self._f(m.get("sharpe", 0.0))
            drawdown = self._f(m.get("drawdown", 0.0))
            trades = int(m.get("trades", 0) or 0)
            if sharpe > self.min_sharpe and drawdown < self.max_drawdown and trades > self.min_trades:
                events.append(
                    {
                        "strategy_id": sid,
                        "promotion_stage": "PAPER_TRADING",
                        "metrics": {
                            "sharpe": round(sharpe, 6),
                            "drawdown": round(drawdown, 6),
                            "trades": trades,
                        },
                    }
                )
        return events

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

