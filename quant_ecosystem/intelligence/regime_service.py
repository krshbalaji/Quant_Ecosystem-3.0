from __future__ import annotations

from typing import Any, Dict, Optional

from quant_ecosystem.market_regime import MarketRegimeDetector
from quant_ecosystem.regime_transition import RegimeTransitionDetector


class RegimeService:
    """Safe additive regime intelligence producer.

    Wraps the market regime and transition detectors and always returns a
    predictable payload, even when one of the underlying detectors fails.
    """

    def __init__(
        self,
        market_regime_detector: Optional[MarketRegimeDetector] = None,
        transition_detector: Optional[RegimeTransitionDetector] = None,
    ) -> None:
        self.market_regime_detector = market_regime_detector or MarketRegimeDetector()
        self.transition_detector = transition_detector or RegimeTransitionDetector()

    def analyze(
        self,
        timeframe_data: Optional[Dict[str, Dict]] = None,
        extra_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        timeframe_data = timeframe_data or {}
        extra_signals = extra_signals or {}

        regime_state = self._safe_detect_regime(timeframe_data, extra_signals)
        transition_state = self._safe_detect_transition(timeframe_data, regime_state.get("regime", "UNKNOWN"))

        return {
            "regime": str(regime_state.get("regime", "UNKNOWN")).upper(),
            "regime_confidence": float(regime_state.get("confidence", 0.0) or 0.0),
            "transition_alert": bool(transition_state.get("transition_alert", False)),
            "transition_score": float(transition_state.get("transition_score", 0.0) or 0.0),
            "transition_type": str(transition_state.get("transition_type", "NONE")).upper(),
            "regime_details": regime_state.get("details") if isinstance(regime_state, dict) else {},
            "transition_details": transition_state.get("components") if isinstance(transition_state, dict) else {},
        }

    def _safe_detect_regime(self, timeframe_data: Dict[str, Dict], extra_signals: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.market_regime_detector.detect_regime(timeframe_data, extra_signals=extra_signals)
            return result or self._fallback_regime_state()
        except Exception:
            try:
                return self.market_regime_detector.get_regime_state()
            except Exception:
                return self._fallback_regime_state()

    def _safe_detect_transition(self, timeframe_data: Dict[str, Dict], current_regime: str) -> Dict[str, Any]:
        try:
            result = self.transition_detector.detect_transition(timeframe_data, current_regime=current_regime)
            return result or self._fallback_transition_state()
        except Exception:
            try:
                return self.transition_detector.get_transition_state()
            except Exception:
                return self._fallback_transition_state()

    @staticmethod
    def _fallback_regime_state() -> Dict[str, Any]:
        return {
            "regime": "UNKNOWN",
            "confidence": 0.0,
            "details": {},
        }

    @staticmethod
    def _fallback_transition_state() -> Dict[str, Any]:
        return {
            "transition_alert": False,
            "transition_score": 0.0,
            "transition_type": "NONE",
            "components": {},
        }
