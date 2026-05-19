import unittest

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.portfolio import PortfolioWatchdog


class PortfolioWatchdogSmokeTests(unittest.TestCase):

    def setUp(self):
        self.watchdog = PortfolioWatchdog()

    def test_profitable_swing_hold(self):
        position = Position(
            symbol="SWING1",
            qty=100,
            avg_entry=100.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.78, "intact": True},
            lifecycle="ACTIVE",
            pnl_unrealized=600.0,
            metadata={"holding_days": 20.0, "trend_proxy": 0.68},
        )

        decision = self.watchdog.evaluate_position(position)
        self.assertEqual(decision.action, "HOLD")
        self.assertEqual(decision.symbol, "SWING1")

    def test_losing_broken_thesis_full_exit(self):
        position = Position(
            symbol="BROKEN1",
            qty=100,
            avg_entry=50.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.20, "intact": False, "exit_signal": True},
            lifecycle="ACTIVE",
            pnl_unrealized=-250.0,
            metadata={"holding_days": 14.0, "trend_proxy": 0.12},
        )

        decision = self.watchdog.evaluate_position(position)
        self.assertEqual(decision.action, "FULL_EXIT")
        self.assertIn("exit risk", decision.reason.lower())

    def test_strong_pullback_intact_thesis_buy_more(self):
        position = Position(
            symbol="PULLBACK1",
            qty=100,
            avg_entry=100.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.72, "intact": True},
            lifecycle="BUILDING",
            pnl_unrealized=-130.0,
            metadata={"holding_days": 10.0, "trend_proxy": 0.55},
        )

        decision = self.watchdog.evaluate_position(position)
        self.assertEqual(decision.action, "BUY_MORE")
        self.assertEqual(decision.symbol, "PULLBACK1")

    def test_flat_dead_capital_rotate(self):
        position = Position(
            symbol="FLAT1",
            qty=100,
            avg_entry=100.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.32, "intact": False},
            lifecycle="ACTIVE",
            pnl_unrealized=5.0,
            metadata={"holding_days": 45.0, "trend_proxy": 0.18},
        )

        decision = self.watchdog.evaluate_position(position)
        self.assertEqual(decision.action, "ROTATE")
        self.assertEqual(decision.symbol, "FLAT1")


if __name__ == "__main__":
    unittest.main()
