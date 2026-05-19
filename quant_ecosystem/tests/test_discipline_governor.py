import time
import unittest

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.discipline import (
    DisciplineAction,
    DisciplineDecision,
    DisciplineState,
    evaluate,
)
from quant_ecosystem.profiles import get_profile


class DisciplineGovernorTests(unittest.TestCase):

    def setUp(self):
        self.state = DisciplineState()
        self.profile = get_profile(ProfileTypes.SCALP)

    def test_allow_for_fresh_signal(self):
        signal = SignalIntent.from_mapping(
            {
                "symbol": "TEST",
                "side": "BUY",
                "profile": ProfileTypes.SCALP,
                "strategy": "TEST",
                "confidence": 0.85,
                "metadata": {"entry_price": 100.0, "atr": 2.0},
            }
        )

        decision = evaluate(signal, self.profile, self.state, market_data={"price": 101.0, "atr": 2.0})

        self.assertEqual(decision.action, DisciplineAction.ALLOW)
        self.assertIn("passed", decision.reason)

    def test_reject_for_extended_move(self):
        signal = SignalIntent.from_mapping(
            {
                "symbol": "TEST",
                "side": "BUY",
                "profile": ProfileTypes.SCALP,
                "strategy": "TEST",
                "confidence": 0.90,
                "metadata": {"entry_price": 100.0, "atr": 2.0},
            }
        )

        decision = evaluate(signal, self.profile, self.state, market_data={"price": 104.0, "atr": 2.0})

        self.assertEqual(decision.action, DisciplineAction.REJECT)
        self.assertIn("anti-chase", decision.reason)

    def test_lock_after_recent_loss(self):
        signal = SignalIntent.from_mapping(
            {
                "symbol": "TEST",
                "side": "SELL",
                "profile": ProfileTypes.SCALP,
                "strategy": "TEST",
                "confidence": 0.60,
                "metadata": {"recent_outcome": "LOSS"},
            }
        )

        decision = evaluate(signal, self.profile, self.state)

        self.assertEqual(decision.action, DisciplineAction.LOCK)
        self.assertIn("revenge guard", decision.reason)

        next_signal = SignalIntent.from_mapping(
            {
                "symbol": "TEST",
                "side": "SELL",
                "profile": ProfileTypes.SCALP,
                "strategy": "TEST",
                "confidence": 0.60,
                "metadata": {},
            }
        )

        locked_decision = evaluate(next_signal, self.profile, self.state)
        self.assertEqual(locked_decision.action, DisciplineAction.LOCK)

    def test_reject_on_daily_trade_limit(self):
        self.state.daily_trades = 3
        self.state.reset_daily_if_needed()

        signal = SignalIntent.from_mapping(
            {
                "symbol": "TEST",
                "side": "BUY",
                "profile": ProfileTypes.SCALP,
                "strategy": "TEST",
                "confidence": 0.80,
                "metadata": {"entry_price": 100.0, "atr": 2.0},
            }
        )

        decision = evaluate(signal, self.profile, self.state, market_data={"price": 101.0, "atr": 2.0})

        self.assertEqual(decision.action, DisciplineAction.REJECT)
        self.assertIn("daily trade limit", decision.reason)


if __name__ == "__main__":
    unittest.main()
