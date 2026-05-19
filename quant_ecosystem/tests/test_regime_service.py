import unittest
from typing import Any, Dict, Optional

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.decision.decision_context import DecisionContext
from quant_ecosystem.discipline import DisciplineDecision, DisciplineAction
from quant_ecosystem.intelligence.regime_service import RegimeService
from quant_ecosystem.profiles import get_profile


class StubMarketRegimeDetector:
    def __init__(self, payload: Dict[str, Any], fallback: Optional[Dict[str, Any]] = None):
        self._payload = payload
        self._fallback = fallback or {"regime": "UNKNOWN", "confidence": 0.0, "details": {}}

    def detect_regime(self, timeframe_data: Dict[str, Dict], extra_signals: Optional[Dict] = None) -> Dict[str, Any]:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def get_regime_state(self) -> Dict[str, Any]:
        return self._fallback


class StubTransitionDetector:
    def __init__(self, payload: Dict[str, Any], fallback: Optional[Dict[str, Any]] = None):
        self._payload = payload
        self._fallback = fallback or {
            "transition_alert": False,
            "transition_score": 0.0,
            "transition_type": "NONE",
            "components": {},
        }

    def detect_transition(self, timeframe_data: Dict[str, Dict], current_regime: str = "UNKNOWN") -> Dict[str, Any]:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def get_transition_state(self) -> Dict[str, Any]:
        return self._fallback


class RegimeServiceTests(unittest.TestCase):

    def test_trending_bull_payload(self):
        market_detector = StubMarketRegimeDetector(
            {"regime": "TRENDING_BULL", "confidence": 0.88, "details": {"trend": "bull"}}
        )
        transition_detector = StubTransitionDetector(
            {"transition_alert": False, "transition_score": 0.12, "transition_type": "NONE"}
        )
        service = RegimeService(market_regime_detector=market_detector, transition_detector=transition_detector)

        payload = service.analyze(timeframe_data={"1h": {"close": [100, 105]}}, extra_signals={})

        self.assertEqual(payload["regime"], "TRENDING_BULL")
        self.assertAlmostEqual(payload["regime_confidence"], 0.88)
        self.assertFalse(payload["transition_alert"])
        self.assertEqual(payload["transition_type"], "NONE")

    def test_crash_event_payload(self):
        market_detector = StubMarketRegimeDetector(
            {"regime": "CRASH_EVENT", "confidence": 0.93, "details": {"event": "selloff"}}
        )
        transition_detector = StubTransitionDetector(
            {"transition_alert": True, "transition_score": 0.78, "transition_type": "TRENDING_TO_REVERSAL"}
        )
        service = RegimeService(market_regime_detector=market_detector, transition_detector=transition_detector)

        payload = service.analyze(timeframe_data={"15m": {"close": [120, 90]}}, extra_signals={})

        self.assertEqual(payload["regime"], "CRASH_EVENT")
        self.assertTrue(payload["transition_alert"])
        self.assertEqual(payload["transition_type"], "TRENDING_TO_REVERSAL")
        self.assertGreater(payload["transition_score"], 0.0)

    def test_volatility_transition_payload(self):
        market_detector = StubMarketRegimeDetector(
            {"regime": "HIGH_VOLATILITY", "confidence": 0.73, "details": {"volatility": "high"}}
        )
        transition_detector = StubTransitionDetector(
            {"transition_alert": True, "transition_score": 0.82, "transition_type": "VOLATILITY_TRANSITION"}
        )
        service = RegimeService(market_regime_detector=market_detector, transition_detector=transition_detector)

        payload = service.analyze(timeframe_data={"5m": {"close": [10, 12, 11]}}, extra_signals={})

        self.assertEqual(payload["regime"], "HIGH_VOLATILITY")
        self.assertTrue(payload["transition_alert"])
        self.assertEqual(payload["transition_type"], "VOLATILITY_TRANSITION")
        self.assertAlmostEqual(payload["transition_score"], 0.82)

    def test_failure_fallback(self):
        market_detector = StubMarketRegimeDetector(Exception("market failure"))
        transition_detector = StubTransitionDetector(Exception("transition failure"))
        service = RegimeService(market_regime_detector=market_detector, transition_detector=transition_detector)

        payload = service.analyze(timeframe_data={"1d": {"close": []}}, extra_signals={})

        self.assertEqual(payload["regime"], "UNKNOWN")
        self.assertEqual(payload["regime_confidence"], 0.0)
        self.assertFalse(payload["transition_alert"])
        self.assertEqual(payload["transition_type"], "NONE")

    def test_decision_context_from_regime_inputs(self):
        market_detector = StubMarketRegimeDetector(
            {"regime": "TRENDING_BULL", "confidence": 0.95, "details": {"trend": "bull"}}
        )
        transition_detector = StubTransitionDetector(
            {"transition_alert": False, "transition_score": 0.22, "transition_type": "NONE"}
        )
        service = RegimeService(market_regime_detector=market_detector, transition_detector=transition_detector)
        profile = get_profile(ProfileTypes.SCALP)
        discipline_decision = DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.5)

        context = DecisionContext.from_regime_inputs(
            profile=profile,
            discipline_decision=discipline_decision,
            regime_service=service,
            timeframe_data={"1h": {"close": [300, 310]}},
        )

        self.assertEqual(context.market_regime, "TRENDING_BULL")
        self.assertAlmostEqual(context.regime_confidence, 0.95)
        self.assertFalse(context.transition_alert)
        self.assertEqual(context.transition_type, "NONE")


if __name__ == "__main__":
    unittest.main()
