from __future__ import annotations

from typing import Dict


class PerformanceAttributionEngine:
    """
    Breaks down PnL by strategy and updates PerformanceStore.
    """

    def __init__(self, performance_store):
        self.store = performance_store

    def attribute_trade(self, trade_record: Dict, equity_before: float) -> None:
        """
        trade_record: a single entry from state.trade_history.
        """
        if not trade_record or equity_before <= 0:
            return
        sid = trade_record.get("strategy_id")
        pnl = float(trade_record.get("cycle_pnl", 0.0))
        if not sid or pnl == 0.0:
            return
        self.store.record_trade(strategy_id=sid, pnl=pnl, equity_before=equity_before)

