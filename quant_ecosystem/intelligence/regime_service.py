from __future__ import annotations

from typing import Any, Dict, Optional

from quant_ecosystem.intelligence.regime_memory import RegimeMemory
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
        regime_memory: Optional[RegimeMemory] = None,
    ) -> None:
        self.market_regime_detector = market_regime_detector or MarketRegimeDetector()
        self.transition_detector = transition_detector or RegimeTransitionDetector()
        self.regime_memory = regime_memory or RegimeMemory()

    def analyze(
        self,
        timeframe_data: Optional[Dict[str, Dict]] = None,
        extra_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        timeframe_data = timeframe_data or {}
        extra_signals = extra_signals or {}

        regime_state = self._safe_detect_regime(timeframe_data, extra_signals)
        raw_regime = str(regime_state.get("regime", "UNKNOWN")).upper()
        regime_label = self._normalize_regime(raw_regime)
        transition_state = self._safe_detect_transition(timeframe_data, raw_regime)

        transition_alert = bool(transition_state.get("transition_alert", False))
        transition_score = float(transition_state.get("transition_score", 0.0) or 0.0)
        regime_mode = "TRANSITION" if transition_alert and transition_score >= 0.65 else "STABLE"

        duration = float(extra_signals.get("regime_duration", 1.0) or 1.0)
        pnl_impact = float(extra_signals.get("pnl_impact", 0.0) or 0.0)
        strategy_id = str(extra_signals.get("strategy_id") or extra_signals.get("strategy") or "UNKNOWN").upper()

        expected_duration = self.regime_memory.expected_duration(regime_label)
        memory_metrics = self.regime_memory.add_regime_event(
            regime=regime_label,
            duration=duration,
            volatility=self._safe_float(regime_state.get("details", {}).get("volatility", None), extra_signals.get("volatility", 0.0)),
            confidence=float(regime_state.get("confidence", 0.0) or 0.0),
            pnl_impact=pnl_impact,
            strategy_id=strategy_id,
            strategy_performance=extra_signals.get("strategy_performance"),
            transition_from=str(transition_state.get("from_regime", "UNKNOWN")).upper(),
            transition_hint=str(transition_state.get("to_regime_hint", "UNKNOWN")).upper(),
        )

        expected_duration = float(expected_duration or 1.0)
        decayed_confidence = self._decayed_confidence(
            float(regime_state.get("confidence", 0.0) or 0.0),
            duration,
            expected_duration,
        )
        late_stage_breakout = regime_label == "VOLATILE_BREAKOUT" and duration >= max(expected_duration * 0.75, 2.0)
        exhausted_trend = regime_label in {"TRENDING_BULLISH", "TRENDING_BEARISH"} and duration >= expected_duration * 1.25

        transition_probabilities = self.regime_memory.transition_probabilities(raw_regime)
        strategy_performance = self.regime_memory.strategy_metrics(strategy_id, regime_label)
        performance_bias = self.regime_memory.strategy_bias(strategy_id, regime_label)

        return {
            "regime": regime_label,
            "regime_v2": regime_label,
            "legacy_regime": raw_regime,
            "regime_mode": regime_mode,
            "regime_confidence": float(regime_state.get("confidence", 0.0) or 0.0),
            "decayed_confidence": decayed_confidence,
            "transition_alert": transition_alert,
            "transition_score": transition_score,
            "transition_type": str(transition_state.get("transition_type", "NONE")).upper(),
            "transition_from": str(transition_state.get("from_regime", "UNKNOWN")).upper(),
            "transition_hint": str(transition_state.get("to_regime_hint", "UNKNOWN")).upper(),
            "regime_details": regime_state.get("details") if isinstance(regime_state, dict) else {},
            "transition_details": transition_state.get("components") if isinstance(transition_state, dict) else {},
            "regime_age": {
                "duration": duration,
                "expected_duration": expected_duration,
                "late_stage_breakout": late_stage_breakout,
                "exhausted_trend": exhausted_trend,
            },
            "performance_bias": performance_bias,
            "strategy_performance": strategy_performance,
            "telemetry": {
                "source": "RegimeService",
                "regime": regime_label,
                "legacy_regime": raw_regime,
                "regime_mode": regime_mode,
                "confidence": float(regime_state.get("confidence", 0.0) or 0.0),
                "decayed_confidence": decayed_confidence,
                "transition_score": transition_score,
                "transition_type": str(transition_state.get("transition_type", "NONE")).upper(),
                "transition_hint": str(transition_state.get("to_regime_hint", "UNKNOWN")).upper(),
                "timeframes": sorted(list(timeframe_data.keys())),
                "transition_probabilities": transition_probabilities,
                "expected_regime_duration": expected_duration,
                "historical_regime_similarity": float(memory_metrics.get("historical_regime_similarity", 0.0) or 0.0),
                "strategy_performance": strategy_performance,
            },
        }

    def _normalize_regime(self, regime: str) -> str:
        normalized = str(regime or "UNKNOWN").upper()
        return {
            "TRENDING_BULL": "TRENDING_BULLISH",
            "TRENDING_BEAR": "TRENDING_BEARISH",
            "TRENDING": "TRENDING_BULLISH",
            "LOW_VOLATILITY": "RANGE_BOUND",
        }.get(normalized, normalized)

    def _safe_float(self, value: Any, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(fallback or 0.0)

    def _decayed_confidence(self, confidence: float, duration: float, expected_duration: float) -> float:
        if expected_duration <= 0 or duration <= expected_duration:
            return round(max(0.0, min(confidence, 1.0)), 4)
        decay = max(0.25, 1.0 - min(0.7, (duration - expected_duration) / max(expected_duration, 1.0) * 0.12))
        return round(max(0.0, min(confidence * decay, 1.0)), 4)

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
            "from_regime": "UNKNOWN",
            "to_regime_hint": "UNKNOWN",
        }
