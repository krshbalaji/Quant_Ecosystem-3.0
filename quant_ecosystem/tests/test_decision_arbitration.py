import unittest

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.decision import ArbitrationAction, ArbitrationEngine
from quant_ecosystem.decision.decision_context import DecisionContext
from quant_ecosystem.discipline import DisciplineDecision, DisciplineAction
from quant_ecosystem.profiles import get_profile
from quant_ecosystem.risk.correlation_guard import CorrelationGuard
from quant_ecosystem.risk.reserve_manager import ReserveManager
from quant_ecosystem.risk.capital_allocator_v2 import CapitalAllocatorV2


class DummyRegimeService:
    def __init__(self, payload: dict):
        self._payload = payload

    def analyze(self, timeframe_data=None, extra_signals=None):
        return self._payload


class DecisionArbitrationTests(unittest.TestCase):

    def setUp(self):
        self.profile = get_profile(ProfileTypes.SCALP)
        self.classifier = ArbitrationEngine()

    def _make_signal(self, symbol, side, profile, confidence, score, rr, notional, metadata=None):
        return SignalIntent.from_mapping(
            {
                "symbol": symbol,
                "side": side,
                "profile": profile,
                "strategy": "TEST",
                "confidence": confidence,
                "metadata": {
                    "score": score,
                    "risk_reward": rr,
                    "notional": notional,
                    **(metadata or {}),
                },
            }
        )

    def test_btc_scalp_vs_btc_multibagger(self):
        scalp_signal = self._make_signal(
            symbol="BTC",
            side="SELL",
            profile=ProfileTypes.SCALP,
            confidence=0.88,
            score=92,
            rr=1.7,
            notional=8_000,
        )
        multibagger_signal = self._make_signal(
            symbol="BTC",
            side="BUY",
            profile=ProfileTypes.MULTIBAGGER,
            confidence=0.80,
            score=85,
            rr=2.5,
            notional=15_000,
        )

        context = DecisionContext.from_regime_inputs(
            profile=self.profile,
            discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.4),
            regime_service=DummyRegimeService(
                {"regime": "BEAR", "confidence": 0.72, "details": {"bearness": True}},
            ),
            capital_allocator=CapitalAllocatorV2(total_capital=100_000.0),
            reserve_manager=ReserveManager(total_capital=100_000.0, reserve_pct=0.05),
            correlation_guard=CorrelationGuard(total_capital=100_000.0),
            portfolio_exposure_pct=25.0,
            risk_state="GREEN",
        )

        decision = self.classifier.arbitrate([scalp_signal, multibagger_signal], context)

        self.assertEqual(decision.action, ArbitrationAction.TAKE)
        self.assertEqual(decision.selected_signal.symbol, "BTC")
        self.assertEqual(decision.selected_signal.side, "SELL")

    def test_morning_scalp_vs_afternoon_aplus_swing(self):
        scalp_signal = self._make_signal(
            symbol="ETH",
            side="BUY",
            profile=ProfileTypes.SCALP,
            confidence=0.82,
            score=78,
            rr=1.4,
            notional=5_000,
            metadata={"time_of_day": "MORNING"},
        )
        swing_signal = self._make_signal(
            symbol="ETH",
            side="BUY",
            profile=ProfileTypes.SWING,
            confidence=0.92,
            score=88,
            rr=2.0,
            notional=12_000,
            metadata={"time_of_day": "AFTERNOON", "premium": True},
        )

        context = DecisionContext.from_regime_inputs(
            profile=self.profile,
            discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.5),
            regime_service=DummyRegimeService(
                {"regime": "BULL", "confidence": 0.88, "details": {"bull_bias": True}},
            ),
            capital_allocator=CapitalAllocatorV2(total_capital=100_000.0, reserve_pct=0.05),
            reserve_manager=ReserveManager(total_capital=100_000.0, reserve_pct=0.05),
            correlation_guard=CorrelationGuard(total_capital=100_000.0),
            portfolio_exposure_pct=40.0,
            risk_state="GREEN",
            reserve_allowed=True,
            is_premium_opportunity=True,
        )

        decision = self.classifier.arbitrate([scalp_signal, swing_signal], context)

        self.assertEqual(decision.action, ArbitrationAction.OVERRIDE)
        self.assertEqual(decision.selected_signal.symbol, "ETH")
        self.assertEqual(decision.selected_signal.profile, ProfileTypes.SWING)

    def test_correlated_crypto_shorts(self):
        guard = CorrelationGuard(total_capital=100_000.0, max_thesis_exposure_pct=0.10, max_group_exposures=2)
        guard.record_exposure("BTC_SHORT", 5_000.0, group="SHORT")
        guard.record_exposure("ETH_SHORT", 5_000.0, group="SHORT")

        short_signal = self._make_signal(
            symbol="SOL",
            side="SELL",
            profile=ProfileTypes.SCALP,
            confidence=0.85,
            score=88,
            rr=1.8,
            notional=2_000,
            metadata={"thesis": "SOL_SHORT", "correlation_group": "SHORT"},
        )

        context = DecisionContext.from_regime_inputs(
            profile=self.profile,
            discipline_decision=DisciplineDecision(action=DisciplineAction.ALLOW, reason="ok", confidence=0.4),
            regime_service=DummyRegimeService(
                {"regime": "BEAR", "confidence": 0.65, "details": {"bear_risk": True}},
            ),
            capital_allocator=CapitalAllocatorV2(total_capital=100_000.0),
            reserve_manager=ReserveManager(total_capital=100_000.0, reserve_pct=0.05),
            correlation_guard=guard,
            portfolio_exposure_pct=30.0,
            risk_state="GREEN",
        )

        decision = self.classifier.arbitrate([short_signal], context)

        self.assertEqual(decision.action, ArbitrationAction.REJECT)
        self.assertIn("correlation guard", decision.reason)

    def test_incompatible_strategy_penalty(self):
        mean_revert_signal = SignalIntent.from_mapping(
            {
                "symbol": "AAPL",
                "side": "BUY",
                "profile": ProfileTypes.SWING,
                "strategy": "MEAN_REVERT",
                "confidence": 0.75,
                "metadata": {"signal_type": "REVERSAL"},
            }
        )

        adjustment = self.classifier._regime_priority_adjustment(mean_revert_signal, "TRENDING_BULLISH")
        self.assertLess(adjustment["priority"], 0.0)


if __name__ == "__main__":
    unittest.main()
