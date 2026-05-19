"""Regime classification logic."""

from __future__ import annotations

from typing import Dict


class RegimeClassifier:
    """Combines trend, volatility, and liquidity into discrete regimes."""

    REGIMES = {
        "TRENDING_BULLISH",
        "TRENDING_BEARISH",
        "RANGE_BOUND",
        "VOLATILE_BREAKOUT",
        "MEAN_REVERSION",
        "ACCUMULATION",
        "DISTRIBUTION",
        "LIQUIDITY_SWEEP",
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
        elif vol_pct >= 90.0 and liq_score < 40.0:
            regime = "LIQUIDITY_SWEEP"
            reason = "Sharp volume and liquidity stress with elevated volatility."
        elif direction in {"BULL", "BEAR"} and trend_strength >= 60.0 and vol_state in {"NORMAL", "LOW"}:
            regime = "TRENDING_BULLISH" if direction == "BULL" else "TRENDING_BEARISH"
            reason = "Stable directional momentum with disciplined volatility."
        elif vol_state == "HIGH" and trend_strength >= 55.0:
            regime = "VOLATILE_BREAKOUT"
            reason = "High volatility with strong directional pressure."
        elif vol_state == "HIGH":
            regime = "HIGH_VOLATILITY"
            reason = "Volatility elevated without a strong directional breakout."
        elif direction == "NEUTRAL" and vol_state == "LOW" and trend_strength < 45.0:
            if liq_score >= 55.0:
                regime = "ACCUMULATION"
                reason = "Compressed action with above-average liquidity and gradual buying."
            else:
                regime = "DISTRIBUTION"
                reason = "Compressed action with weaker liquidity and potential supply build-up."
        elif direction == "NEUTRAL" and vol_state in {"NORMAL", "HIGH"} and trend_strength < 55.0:
            regime = "MEAN_REVERSION"
            reason = "Sideways pressure with normal-to-elevated volatility ideal for range reversion."
        elif trend_strength < 40.0:
            regime = "RANGE_BOUND"
            reason = "Weak directional trend with muted volatility."
        elif direction == "BULL":
            regime = "TRENDING_BULLISH"
            reason = "Bullish momentum remains the dominant regime."
        elif direction == "BEAR":
            regime = "TRENDING_BEARISH"
            reason = "Bearish momentum remains the dominant regime."

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
        if regime in {"TRENDING_BULLISH", "TRENDING_BEARISH"}:
            base += min(0.35, trend_strength / 220.0)
        elif regime == "CRASH_EVENT":
            base += min(0.4, vol_pct / 190.0)
        elif regime == "VOLATILE_BREAKOUT":
            base += min(0.35, vol_pct / 180.0) + min(0.15, trend_strength / 200.0)
        elif regime == "HIGH_VOLATILITY":
            base += min(0.25, vol_pct / 220.0)
        elif regime in {"ACCUMULATION", "DISTRIBUTION"}:
            base += min(0.18, liq_score / 450.0)
        elif regime == "MEAN_REVERSION":
            base += min(0.22, (100.0 - trend_strength) / 200.0)
        elif regime == "LIQUIDITY_SWEEP":
            base += min(0.3, vol_pct / 180.0)
        else:
            base += min(0.18, liq_score / 500.0)
        return round(max(0.0, min(base, 0.99)), 4)
