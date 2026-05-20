from __future__ import annotations

from typing import Any, Dict, Optional


class RegimeClassifier:
    def classify(
        self,
        market_snapshot: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        market_snapshot = market_snapshot or {}

        trend = kwargs.get("trend", {})
        volatility = kwargs.get("volatility", {})
        liquidity = kwargs.get("liquidity", {})
        extra = kwargs.get("extra", {})

        trend_strength = self._safe_float(
            trend.get("trend_strength"),
            default=0.0,
        )

        trend_direction = str(
            trend.get("trend_direction", "NEUTRAL")
        ).upper()

        volatility_state = str(
            volatility.get("volatility_state", "NORMAL")
        ).upper()

        volatility_percentile = self._safe_float(
            volatility.get("volatility_percentile"),
            default=0.0,
        )

        liquidity_score = self._safe_float(
            liquidity.get("liquidity_score"),
            default=0.0,
        )

        market_breadth = self._safe_float(
            extra.get("market_breadth"),
            default=0.0,
        )

        regime = "RANGE_BOUND"
        confidence = 0.50

        if (
            trend_strength >= 60
            and volatility_state == "HIGH"
            and volatility_percentile >= 80
        ):
            regime = "VOLATILE_BREAKOUT"
            confidence = 0.82

        elif (
            trend_direction in {"BULL", "TRENDING_BULL"}
            and trend_strength >= 45
        ):
            regime = "TRENDING_BULLISH"
            confidence = 0.84

        elif (
            trend_direction in {"BEAR", "TRENDING_BEAR"}
            and trend_strength >= 45
        ):
            regime = "TRENDING_BEARISH"
            confidence = 0.84

        elif (
            trend_direction == "NEUTRAL"
            and volatility_state == "LOW"
            and liquidity_score >= 60
        ):
            regime = "ACCUMULATION"
            confidence = 0.72

        elif abs(market_breadth) > 0.05:
            regime = "TRANSITION"
            confidence = 0.65

        return {
            "regime": regime,
            "confidence": confidence,
            "details": {
                "trend_strength": trend_strength,
                "trend_direction": trend_direction,
                "volatility_state": volatility_state,
                "volatility_percentile": volatility_percentile,
                "liquidity_score": liquidity_score,
                "market_breadth": market_breadth,
            },
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default