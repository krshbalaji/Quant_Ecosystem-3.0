from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PerformanceRecord:
    returns: List[float] = field(default_factory=list)
    pnl: float = 0.0
    wins: int = 0
    losses: int = 0

    def update(self, ret: float) -> None:
        self.returns.append(ret)
        self.pnl += ret
        if ret > 0:
            self.wins += 1
        elif ret < 0:
            self.losses += 1

    def metrics(self) -> Dict[str, float]:
        if not self.returns:
            return {
                "daily_pnl": 0.0,
                "sharpe": 0.0,
                "drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
            }
        rets = self.returns
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r < 0]
        win_rate = (len(wins) / len(rets)) * 100.0 if rets else 0.0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        import math

        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / max(1, len(rets) - 1)
        std = math.sqrt(var)
        sharpe = (mean / std * (252 ** 0.5)) if std > 0 else 0.0

        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in rets:
            equity *= 1 + r
            peak = max(peak, equity)
            if peak > 0:
                dd = (peak - equity) / peak * 100.0
                max_dd = max(max_dd, dd)

        return {
            "daily_pnl": self.pnl,
            "sharpe": round(sharpe, 4),
            "drawdown": round(max_dd, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
        }


class PerformanceStore:
    """
    Lightweight in-memory performance store keyed by strategy_id.
    """

    def __init__(self) -> None:
        self._records: Dict[str, PerformanceRecord] = defaultdict(PerformanceRecord)

    def record_trade(self, strategy_id: str, pnl: float, equity_before: float) -> None:
        if equity_before <= 0:
            return
        ret = float(pnl) / float(equity_before)
        self._records[str(strategy_id)].update(ret)

    def get_metrics(self, strategy_id: str) -> Dict[str, float]:
        rec = self._records.get(str(strategy_id))
        return rec.metrics() if rec else PerformanceRecord().metrics()

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        return {sid: rec.metrics() for sid, rec in self._records.items()}

