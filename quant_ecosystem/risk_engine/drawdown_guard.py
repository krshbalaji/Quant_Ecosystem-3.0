"""Portfolio and strategy drawdown guards."""

from __future__ import annotations

from typing import Dict, Iterable, List


class DrawdownGuard:
    """Evaluates drawdown constraints for portfolio and strategies."""

    def __init__(self, portfolio_dd_limit_pct: float = 20.0, strategy_dd_limit_pct: float = 10.0):
        self.portfolio_dd_limit_pct = float(portfolio_dd_limit_pct)
        self.strategy_dd_limit_pct = float(strategy_dd_limit_pct)

    def evaluate_portfolio(self, state) -> Dict:
        drawdown = float(getattr(state, "total_drawdown_pct", 0.0))
        breached = drawdown >= self.portfolio_dd_limit_pct
        return {
            "drawdown_pct": round(drawdown, 4),
            "limit_pct": round(self.portfolio_dd_limit_pct, 4),
            "breached": breached,
            "action": "EMERGENCY_REDUCE_AND_PAUSE" if breached else "NONE",
        }

    def evaluate_strategies(self, trades: Iterable[Dict]) -> Dict[str, Dict]:
        by_strategy: Dict[str, List[float]] = {}
        for trade in trades:
            sid = str(trade.get("strategy") or trade.get("strategy_id") or "").strip()
            if not sid:
                continue
            pnl = float(trade.get("cycle_pnl", 0.0))
            by_strategy.setdefault(sid, []).append(pnl)

        out: Dict[str, Dict] = {}
        for sid, pnls in by_strategy.items():
            dd = self._max_drawdown_pct(pnls)
            breached = dd >= self.strategy_dd_limit_pct
            out[sid] = {
                "strategy_drawdown_pct": round(dd, 4),
                "limit_pct": round(self.strategy_dd_limit_pct, 4),
                "breached": breached,
                "action": "REDUCE_ALLOCATION" if breached else "NONE",
            }
        return out

    def _max_drawdown_pct(self, pnls: List[float]) -> float:
        if not pnls:
            return 0.0
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in pnls:
            equity += float(pnl)
            peak = max(peak, equity)
            if peak > 0:
                dd = ((peak - equity) / peak) * 100.0
                max_dd = max(max_dd, dd)
        return max_dd

