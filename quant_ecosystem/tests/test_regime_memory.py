import json
import os
import tempfile
import unittest

from quant_ecosystem.decision.arbitration_engine import ArbitrationAction, ArbitrationEngine
from quant_ecosystem.decision.decision_context import DecisionContext
from quant_ecosystem.discipline import DisciplineDecision, DisciplineAction
from quant_ecosystem.intelligence.regime_memory import RegimeMemory
from quant_ecosystem.intelligence.regime_service import RegimeService
from quant_ecosystem.profiles import get_profile
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import SignalIntent
from typing import cast

from quant_ecosystem.market_regime.regime_detector import MarketRegimeDetector
from quant_ecosystem.regime_transition.transition_detector import RegimeTransitionDetector

class StubMarketRegimeDetector:
    def detect_regime(self, timeframe_data, extra_signals=None):
        return {"regime": "TRENDING_BULL", "confidence": 0.80, "details": {"volatility": 25.0}}

    def get_regime_state(self):
        return {"regime": "TRENDING_BULL", "confidence": 0.80, "details": {"volatility": 25.0}}


class StubTransitionDetector:
    def detect_transition(self, timeframe_data, current_regime="UNKNOWN"):
        return {
            "transition_alert": False,
            "transition_score": 0.20,
            "transition_type": "NONE",
            "from_regime": current_regime,
            "to_regime_hint": current_regime,
            "components": {},
        }

    def get_transition_state(self):
        return {
            "transition_alert": False,
            "transition_score": 0.0,
            "transition_type": "NONE",
            "components": {},
            "from_regime": "UNKNOWN",
            "to_regime_hint": "UNKNOWN",
        }


class RegimeMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp_dir.name, "regime_memory.json")
        self.memory = RegimeMemory(path=self.path, max_history=3)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_regime_memory_rollover(self):
        for i in range(4):
            self.memory.add_regime_event(
                regime="RANGE_BOUND",
                duration=1.0 + i,
                volatility=10.0 + i,
                confidence=0.5 + 0.1 * i,
                pnl_impact=0.0,
                strategy_id="TEST",
            )

        self.assertEqual(len(self.memory.history), 3)
        self.assertNotEqual(self.memory.history[0]["duration"], 1.0)

    def test_transition_probability_updates(self):
        self.memory.record_transition("TRENDING_BULLISH", "DISTRIBUTION")
        self.memory.record_transition("TRENDING_BULLISH", "DISTRIBUTION")
        self.memory.record_transition("TRENDING_BULLISH", "VOLATILE_BREAKOUT")

        probabilities = self.memory.transition_probabilities("TRENDING_BULLISH")
        self.assertAlmostEqual(probabilities.get("DISTRIBUTION", 0.0), 0.6667, places=4)
        self.assertAlmostEqual(probabilities.get("VOLATILE_BREAKOUT", 0.0), 0.3333, places=4)

    def test_adaptive_confidence_decay(self):
        service = RegimeService(
            market_regime_detector=cast(
                MarketRegimeDetector,
                StubMarketRegimeDetector(),
            ),
            transition_detector=cast(
                RegimeTransitionDetector,
                StubTransitionDetector(),
            ),
            regime_memory=self.memory,
        )
        payload = service.analyze(
            timeframe_data={"1h": {"close": [1, 2, 3]}},
            extra_signals={"regime_duration": 10.0, "strategy_id": "TEST"},
        )

        self.assertEqual(payload["telemetry"]["expected_regime_duration"], 8.0)
        self.assertLess(payload["decayed_confidence"], payload["regime_confidence"])
        self.assertIn("transition_probabilities", payload["telemetry"])

    def test_strong_strategy_performance_boost(self):
        for pnl in [10.0, 10.0, 10.0, 10.0, -5.0, -5.0]:
            self.memory.add_regime_event(
                regime="TRENDING_BULLISH",
                duration=1.0,
                volatility=12.0,
                confidence=0.75,
                pnl_impact=pnl,
                strategy_id="STRONG",
            )

        signal = SignalIntent.from_mapping(
            {
                "symbol": "AAPL",
                "side": "BUY",
                "profile": ProfileTypes.SWING,
                "strategy": "STRONG",
                "confidence": 0.82,
                "metadata": {"signal_type": "BREAKOUT", "risk_reward": 1.8},
            }
        )

        context = DecisionContext(
            profile=get_profile(ProfileTypes.SCALP),
            discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.5),
            regime_memory=self.memory,
            market_regime="TRENDING_BULLISH",
            regime_confidence=0.85,
            risk_state="GREEN",
        )

        decision = ArbitrationEngine().arbitrate([signal], context)
        self.assertEqual(decision.action, ArbitrationAction.TAKE)

    def test_weak_strategy_performance_reject(self):
        for pnl in [-5.0] * 12:
            self.memory.add_regime_event(
                regime="MEAN_REVERSION",
                duration=1.0,
                volatility=8.0,
                confidence=0.55,
                pnl_impact=pnl,
                strategy_id="WEAK",
            )

        signal = SignalIntent.from_mapping(
            {
                "symbol": "MSFT",
                "side": "SELL",
                "profile": ProfileTypes.INTRADAY,
                "strategy": "WEAK",
                "confidence": 0.60,
                "metadata": {"signal_type": "REVERSAL", "risk_reward": 1.4},
            }
        )

        context = DecisionContext(
            profile=get_profile(ProfileTypes.INTRADAY),
            discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.5),
            regime_memory=self.memory,
            market_regime="MEAN_REVERSION",
            regime_confidence=0.60,
            risk_state="GREEN",
        )

        decision = ArbitrationEngine().arbitrate([signal], context)
        self.assertEqual(decision.action, ArbitrationAction.REJECT)


if __name__ == "__main__":
    unittest.main()
