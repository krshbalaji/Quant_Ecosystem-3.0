"""Global liquidity monitor."""

from __future__ import annotations

from typing import Dict, Iterable


class LiquidityMonitor:
    """Tracks global liquidity via volume/volatility/spreads/rates proxies."""

    def evaluate(self, snapshots: Iterable[Dict], macro_inputs: Dict | None = None) -> Dict:
        rows = list(snapshots or [])
        macro = dict(macro_inputs or {})

        vols = [self._f(r.get("volume", 0.0)) for r in rows]
        volatilities = [self._f(r.get("volatility", 0.0)) for r in rows]
        spreads = [self._f(r.get("spread_bps", r.get("spread", 0.0))) for r in rows]

        avg_volume = (sum(vols) / len(vols)) if vols else 0.0
        avg_volatility = (sum(volatilities) / len(volatilities)) if volatilities else 0.0
        avg_spread = (sum(spreads) / len(spreads)) if spreads else 0.0

        credit_spread = self._f(macro.get("credit_spread_bps", 120.0))
        policy_rate = self._f(macro.get("policy_rate_pct", 6.0))

        # Higher spreads/vol/policy/credit = weaker liquidity.
        liquidity_score = 1.0
        liquidity_score -= min(0.35, avg_volatility * 0.8)
        liquidity_score -= min(0.30, avg_spread / 200.0)
        liquidity_score -= min(0.20, credit_spread / 800.0)
        liquidity_score -= min(0.15, policy_rate / 20.0)
        if avg_volume > 0:
            liquidity_score += min(0.20, avg_volume / 2_000_000.0)
        liquidity_score = max(0.0, min(1.0, liquidity_score))

        if liquidity_score >= 0.65:
            state = "LIQUID"
        elif liquidity_score >= 0.4:
            state = "NEUTRAL"
        else:
            state = "TIGHT"
        return {
            "liquidity_score": round(liquidity_score, 6),
            "liquidity_state": state,
            "avg_volume": round(avg_volume, 6),
            "avg_volatility": round(avg_volatility, 6),
            "avg_spread_bps": round(avg_spread, 6),
            "credit_spread_bps": round(credit_spread, 6),
            "policy_rate_pct": round(policy_rate, 6),
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

