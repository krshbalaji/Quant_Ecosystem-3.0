"""Regime transition detector.

Detects early shifts such as:
- LOW_VOL -> HIGH_VOL
- RANGE_BOUND -> TRENDING
- TRENDING -> REVERSAL
and broadcasts transition signals to downstream engines.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from quant_ecosystem.regime_transition.trend_shift_detector import TrendShiftDetector
from quant_ecosystem.regime_transition.volatility_shift_detector import VolatilityShiftDetector


class RegimeTransitionDetector:
    """Combines volatility/trend/volume shifts into a transition alert score."""

    def __init__(
        self,
        volatility_shift_detector: Optional[VolatilityShiftDetector] = None,
        trend_shift_detector: Optional[TrendShiftDetector] = None,
        transition_threshold: float = 0.60, **kwargs
    ):
        self.volatility_shift_detector = volatility_shift_detector or VolatilityShiftDetector()
        self.trend_shift_detector = trend_shift_detector or TrendShiftDetector()
        self.transition_threshold = max(0.0, min(1.0, float(transition_threshold)))
        self._last_state: Dict = {
            "transition_alert": False,
            "transition_score": 0.0,
            "transition_type": "NONE",
            "from_regime": "UNKNOWN",
            "to_regime_hint": "UNKNOWN",
            "timestamp": None,
        }

    def detect_transition(
        self,
        timeframe_data: Dict[str, Dict],
        current_regime: str = "RANGE_BOUND",
    ) -> Dict:
        """Detect early regime transitions from multi-timeframe inputs."""
        merged = self._merge_timeframes(timeframe_data)
        if not merged.get("close"):
            return dict(self._last_state)

        vol = self.volatility_shift_detector.detect(merged)
        trend = self.trend_shift_detector.detect(merged)
        volume_spike = self._volume_spike(merged)

        # Required formula:
        # transition_score = volatility_acceleration * 0.4 + trend_shift * 0.3 + volume_spike * 0.3
        transition_score = (
            float(vol.get("vol_shift_score", 0.0)) * 0.4
            + float(trend.get("trend_shift", 0.0)) * 0.3
            + float(volume_spike) * 0.3
        )
        transition_score = min(1.0, max(0.0, transition_score))
        transition_alert = transition_score >= self.transition_threshold

        transition_type, to_regime_hint = self._classify_transition(
            current_regime=str(current_regime or "RANGE_BOUND").upper(),
            vol=vol,
            trend=trend,
            transition_alert=transition_alert,
        )

        state = {
            "transition_alert": transition_alert,
            "transition_score": round(transition_score, 6),
            "transition_threshold": self.transition_threshold,
            "transition_type": transition_type,
            "from_regime": str(current_regime or "RANGE_BOUND").upper(),
            "to_regime_hint": to_regime_hint,
            "components": {
                "volatility": vol,
                "trend": trend,
                "volume_spike": round(volume_spike, 6),
            },
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._last_state = dict(state)
        return state

    def get_transition_state(self) -> Dict:
        return dict(self._last_state)

    def broadcast_transition(
        self,
        state: Optional[Dict] = None,
        adaptive_regime_engine=None,
        meta_strategy_brain=None,
        portfolio_ai=None,
    ) -> Dict:
        """Broadcast transition signal via loose coupling.

        No hard dependency on downstream module methods; if dedicated ingestion
        methods exist they are used, otherwise state is attached as attributes.
        """
        payload = dict(state or self._last_state)
        if not payload:
            return {}

        if adaptive_regime_engine is not None:
            try:
                if hasattr(adaptive_regime_engine, "ingest_transition_signal"):
                    adaptive_regime_engine.ingest_transition_signal(payload)
                else:
                    setattr(adaptive_regime_engine, "last_transition_signal", payload)
            except Exception:
                pass

        if meta_strategy_brain is not None:
            try:
                if hasattr(meta_strategy_brain, "ingest_transition_signal"):
                    meta_strategy_brain.ingest_transition_signal(payload)
                else:
                    setattr(meta_strategy_brain, "last_transition_signal", payload)
            except Exception:
                pass

        if portfolio_ai is not None:
            try:
                if hasattr(portfolio_ai, "ingest_transition_signal"):
                    portfolio_ai.ingest_transition_signal(payload)
                else:
                    setattr(portfolio_ai, "last_transition_signal", payload)
            except Exception:
                pass

        return payload

    def _classify_transition(self, current_regime: str, vol: Dict, trend: Dict, transition_alert: bool):
        if not transition_alert:
            return "NONE", current_regime

        vol_shift = float(vol.get("vol_shift_score", 0.0))
        trend_shift = float(trend.get("trend_shift", 0.0))
        reversal_risk = float(trend.get("reversal_risk", 0.0))

        if current_regime in {"LOW_VOLATILITY", "LOW_VOL"} and vol_shift >= 0.65:
            return "LOW_VOL_TO_HIGH_VOL", "HIGH_VOLATILITY"
        if current_regime in {"RANGE_BOUND", "RANGING"} and trend_shift >= 0.60:
            direction = str(trend.get("trend_direction_recent", "UP")).upper()
            return "RANGE_TO_TRENDING", "TRENDING_BULL" if direction == "UP" else "TRENDING_BEAR"
        if current_regime in {"TRENDING_BULL", "TRENDING_BEAR", "TRENDING"} and reversal_risk >= 0.55:
            return "TRENDING_TO_REVERSAL", "RANGE_BOUND"

        # Generic fallbacks
        if vol_shift >= trend_shift:
            return "VOLATILITY_TRANSITION", "HIGH_VOLATILITY"
        return "TREND_TRANSITION", "TRENDING_BULL"

    def _merge_timeframes(self, timeframe_data: Dict[str, Dict]) -> Dict:
        order = ["5m", "15m", "1h", "1d"]
        merged = {"close": [], "high": [], "low": [], "volume": []}
        for tf in order:
            bucket = timeframe_data.get(tf, {}) or {}
            for key in merged.keys():
                values = bucket.get(key, [])
                if not values:
                    continue
                merged[key].extend(values[-40:])
        for key in merged.keys():
            merged[key] = merged[key][-220:]
        return merged

    def _volume_spike(self, snapshot: Dict) -> float:
        volume = [float(x) for x in snapshot.get("volume", []) if self._is_num(x)]
        if len(volume) < 25:
            return 0.0
        recent = volume[-1]
        base = volume[-21:-1]
        mean = sum(base) / len(base)
        if mean <= 1e-9:
            return 0.0
        spike = max(0.0, (recent - mean) / mean)
        return min(1.0, spike / 1.2)

    def _is_num(self, value) -> bool:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False

