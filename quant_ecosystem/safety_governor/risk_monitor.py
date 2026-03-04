"""Portfolio/risk monitor for Safety Governor."""

from __future__ import annotations

from typing import Dict, List


class RiskMonitor:
    """Tracks drawdown, exposure, and leverage-like pressure."""

    def __init__(
        self,
        max_drawdown_limit: float = 20.0,
        max_exposure_pct: float = 90.0,
        max_leverage_like: float = 1.5,
    ):
        self.max_drawdown_limit = float(max_drawdown_limit)
        self.max_exposure_pct = float(max_exposure_pct)
        self.max_leverage_like = float(max_leverage_like)

    def evaluate(self, router, context: Dict | None = None) -> List[Dict]:
        state = getattr(router, "state", None)
        if state is None:
            return []

        equity = self._f(getattr(state, "equity", 0.0))
        exposure_notional = self._f(getattr(state, "open_positions", 0.0))
        if isinstance(exposure_notional, dict):
            exposure_notional = sum(abs(self._f(v)) for v in exposure_notional.values())
        exposure_pct = (exposure_notional / equity * 100.0) if equity > 0 else 0.0

        drawdown = self._f(getattr(state, "total_drawdown_pct", 0.0))
        cap = self._f(getattr(state, "capital_cap", 0.0))
        leverage_like = (equity / cap) if cap > 0 else 0.0

        alerts: List[Dict] = []
        if drawdown > self.max_drawdown_limit:
            alerts.append(
                {
                    "monitor": "risk_monitor",
                    "level": "THROTTLE",
                    "reason": f"Drawdown {round(drawdown, 2)}% > limit {round(self.max_drawdown_limit, 2)}%",
                    "metrics": {"drawdown_pct": round(drawdown, 4)},
                }
            )
        if exposure_pct > self.max_exposure_pct:
            alerts.append(
                {
                    "monitor": "risk_monitor",
                    "level": "RESTRICT",
                    "reason": f"Exposure {round(exposure_pct, 2)}% > limit {round(self.max_exposure_pct, 2)}%",
                    "metrics": {"exposure_pct": round(exposure_pct, 4)},
                }
            )
        if leverage_like > self.max_leverage_like:
            alerts.append(
                {
                    "monitor": "risk_monitor",
                    "level": "RESTRICT",
                    "reason": f"Leverage-like ratio {round(leverage_like, 3)} > limit {round(self.max_leverage_like, 3)}",
                    "metrics": {"leverage_like": round(leverage_like, 6)},
                }
            )
        return alerts

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

