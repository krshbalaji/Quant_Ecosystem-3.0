"""Regime classification logic."""

from __future__ import annotations

from typing import Dict


class RegimeClassifier:
    """Combines trend, volatility, and liquidity into discrete regimes."""

    REGIMES = {
        "TRENDING_BULL",
        "TRENDING_BEAR",
        "RANGE_BOUND",
        "HIGH_VOLATILITY",
        "LOW_VOLATILITY",
        "CRASH_EVENT",
    }

    def classify(self, trend: Dict, volatility: Dict, liquidity: Dict, extra: Dict | None = None) -> Dict:
        extra = extra or {}
        trend_strength = float(trend.get("trend_strength", 0.0))
        direction = str(trend.get("trend_direction", "NEUTRAL")).upper()
        vol_state = str(volatility.get("volatility_state", "NORMAL")).upper()
        vol_pct = float(volatility.get("volatility_percentile", 50.0))
        liq_score = float(liquidity.get("liquidity_score", 50.0))
        breadth = float(extra.get("market_breadth", 0.0))
        vix = float(extra.get("vix", 0.0)) if extra.get("vix") is not None else 0.0

        regime = "RANGE_BOUND"
        reason = "Default range classification."

        crash_trigger = (vol_pct >= 97.0) or (vol_state == "HIGH" and liq_score < 35.0) or (vix >= 35.0)
        if crash_trigger:
            regime = "CRASH_EVENT"
            reason = "Extreme volatility with liquidity stress."
        elif vol_state == "HIGH" and trend_strength < 55.0:
            regime = "HIGH_VOLATILITY"
            reason = "Volatility elevated without stable directional trend."
        elif direction == "BULL" and trend_strength >= 60.0 and vol_state in {"NORMAL", "LOW"} and breadth >= -0.1:
            regime = "TRENDING_BULL"
            reason = "Strong bullish trend with controlled volatility."
        elif direction == "BEAR" and trend_strength >= 60.0 and vol_state in {"NORMAL", "LOW"}:
            regime = "TRENDING_BEAR"
            reason = "Strong bearish trend with controlled volatility."
        elif trend_strength < 40.0 and vol_state == "LOW":
            regime = "RANGE_BOUND"
            reason = "Weak trend and compressed volatility."
        elif vol_state == "LOW":
            regime = "LOW_VOLATILITY"
            reason = "Low volatility regime outside strong trend conditions."

        confidence = self._confidence(regime, trend_strength, vol_pct, liq_score)
        return {
            "regime": regime,
            "confidence": confidence,
            "reason": reason,
            "signals": {
                "trend_strength": trend_strength,
                "trend_direction": direction,
                "volatility_state": vol_state,
                "volatility_percentile": vol_pct,
                "liquidity_score": liq_score,
                "market_breadth": breadth,
                "vix": vix,
            },
        }

    def _confidence(self, regime: str, trend_strength: float, vol_pct: float, liq_score: float) -> float:
        base = 0.55
        if regime in {"TRENDING_BULL", "TRENDING_BEAR"}:
            base += min(0.35, trend_strength / 250.0)
        elif regime == "CRASH_EVENT":
            base += min(0.4, vol_pct / 200.0)
        elif regime == "HIGH_VOLATILITY":
            base += min(0.3, vol_pct / 250.0)
        else:
            base += min(0.2, liq_score / 500.0)
        return round(max(0.0, min(base, 0.99)), 4)
