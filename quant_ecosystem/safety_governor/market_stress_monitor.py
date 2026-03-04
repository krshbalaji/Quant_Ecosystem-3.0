"""Market stress monitor for volatility/spread/liquidity shocks."""

from __future__ import annotations

from typing import Dict, List


class MarketStressMonitor:
    """Detects abnormal market stress conditions."""

    def __init__(
        self,
        volatility_spike_limit: float = 0.35,
        spread_widen_limit_bps: float = 25.0,
        min_liquidity_score: float = 0.2,
    ):
        self.volatility_spike_limit = float(volatility_spike_limit)
        self.spread_widen_limit_bps = float(spread_widen_limit_bps)
        self.min_liquidity_score = float(min_liquidity_score)

    def evaluate(self, router, context: Dict | None = None) -> List[Dict]:
        ctx = dict(context or {})
        intel = dict(ctx.get("intelligence_report", {}) or {})
        snapshots = list(ctx.get("snapshots", []) or [])

        vol = self._f(intel.get("volatility", 0.0))
        spreads = [self._f(row.get("spread_bps", row.get("spread", 0.0))) for row in snapshots]
        avg_spread_bps = (sum(spreads) / len(spreads)) if spreads else 0.0

        liquidities = [self._f(row.get("liquidity_score", 1.0)) for row in snapshots]
        min_liq = min(liquidities) if liquidities else 1.0

        alerts: List[Dict] = []
        if vol > self.volatility_spike_limit:
            alerts.append(
                {
                    "monitor": "market_stress_monitor",
                    "level": "THROTTLE",
                    "reason": (
                        f"Volatility spike {round(vol, 4)} > "
                        f"limit {round(self.volatility_spike_limit, 4)}"
                    ),
                    "metrics": {"volatility": round(vol, 6)},
                }
            )
        if avg_spread_bps > self.spread_widen_limit_bps:
            alerts.append(
                {
                    "monitor": "market_stress_monitor",
                    "level": "RESTRICT",
                    "reason": (
                        f"Spread widened to {round(avg_spread_bps, 2)} bps > "
                        f"limit {round(self.spread_widen_limit_bps, 2)} bps"
                    ),
                    "metrics": {"avg_spread_bps": round(avg_spread_bps, 6)},
                }
            )
        if min_liq < self.min_liquidity_score:
            alerts.append(
                {
                    "monitor": "market_stress_monitor",
                    "level": "RESTRICT",
                    "reason": (
                        f"Liquidity score dropped to {round(min_liq, 4)} < "
                        f"limit {round(self.min_liquidity_score, 4)}"
                    ),
                    "metrics": {"min_liquidity_score": round(min_liq, 6)},
                }
            )
        return alerts

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

