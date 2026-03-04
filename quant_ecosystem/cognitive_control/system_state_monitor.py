"""System state monitor for cognitive control."""

from __future__ import annotations

import time
from typing import Dict


class SystemStateMonitor:
    """Collects real-time state from router/modules."""

    def collect(self, router) -> Dict:
        state = getattr(router, "state", None)
        risk_engine = getattr(router, "risk_engine", None)
        strategy_engine = getattr(router, "strategy_engine", None)
        market_pulse = getattr(router, "market_pulse_engine", None)

        start = time.perf_counter()
        volatility_level = 0.0
        try:
            symbol = (getattr(router, "symbols", []) or ["NSE:NIFTY50-INDEX"])[0]
            snapshots = router._build_snapshots(regime="MEAN_REVERSION") if hasattr(router, "_build_snapshots") else []
            if snapshots:
                volatility_level = max(float(item.get("volatility", 0.0)) for item in snapshots)
            elif getattr(router, "market_data", None):
                volatility_level = float(router.market_data.estimate_volatility(symbol, lookback=30))
        except Exception:
            volatility_level = 0.0

        exec_latency_ms = (time.perf_counter() - start) * 1000.0
        active_count = len(getattr(strategy_engine, "active_ids", []) or [])
        drawdown = float(getattr(state, "total_drawdown_pct", 0.0)) if state else 0.0
        equity = float(getattr(state, "equity", 0.0)) if state else 0.0
        risk_pct = float(getattr(risk_engine, "max_trade_risk", 0.0)) if risk_engine else 0.0
        pulse_events = len(getattr(market_pulse, "last_events", []) or []) if market_pulse else 0

        return {
            "volatility_level": round(volatility_level, 6),
            "portfolio_drawdown": round(drawdown, 6),
            "active_strategies": int(active_count),
            "execution_latency_ms": round(exec_latency_ms, 3),
            "equity": round(equity, 4),
            "risk_pct": round(risk_pct, 4),
            "pulse_events": int(pulse_events),
        }

