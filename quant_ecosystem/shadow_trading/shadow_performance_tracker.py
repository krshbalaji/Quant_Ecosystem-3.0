"""Performance tracker for shadow strategies."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List


class ShadowPerformanceTracker:
    """Computes win rate, PF, Sharpe, drawdown for shadow strategies."""

    def __init__(self, **kwargs):
        self.trades_by_strategy: Dict[str, List[Dict]] = defaultdict(list)

    def record(self, row: Dict) -> None:
        sid = str(row.get("strategy_id", ""))
        if not sid:
            return
        self.trades_by_strategy[sid].append(dict(row))
        self.trades_by_strategy[sid] = self.trades_by_strategy[sid][-4000:]

    def metrics(self, strategy_id: str) -> Dict:
        rows = list(self.trades_by_strategy.get(str(strategy_id), []) or [])
        if not rows:
            return {
                "trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "drawdown": 0.0,
            }
        pnls = [self._f(item.get("pnl", item.get("realized_pnl", 0.0))) for item in rows]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        win_rate = len(wins) / max(1, len(pnls))
        pf = (sum(wins) / sum(losses)) if losses else (10.0 if wins else 0.0)

        mean = sum(pnls) / max(1, len(pnls))
        var = sum((p - mean) ** 2 for p in pnls) / max(1, len(pnls))
        std = math.sqrt(max(var, 1e-12))
        sharpe = (mean / std) * math.sqrt(252.0) if std > 0 else 0.0

        curve = 0.0
        peak = 0.0
        dd = 0.0
        for p in pnls:
            curve += p
            peak = max(peak, curve)
            dd = max(dd, peak - curve)
        return {
            "trades": len(rows),
            "win_rate": round(win_rate, 6),
            "profit_factor": round(pf, 6),
            "sharpe": round(sharpe, 6),
            "drawdown": round(dd, 6),
        }

    def all_metrics(self) -> Dict[str, Dict]:
        return {sid: self.metrics(sid) for sid in list(self.trades_by_strategy.keys())}

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

