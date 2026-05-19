import unittest

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.portfolio import (
    DeadMoneyDetector,
    ProfitProtector,
    ConvictionScaler,
)


class PortfolioCapitalEfficiencyTests(unittest.TestCase):

    def setUp(self):
        self.dead_money = DeadMoneyDetector(min_holding_days=10, max_flat_pct=0.05, max_trend_proxy=0.30)
        self.protector = ProfitProtector(breakeven_pct=0.01, partial_book_pct=0.08, lock_gain_pct=0.15)
        self.scaler = ConvictionScaler(max_add_count=2, min_trend_proxy=0.40)

    def test_dead_money_identified(self):
        position = Position(
            symbol="FLAT_CAP",
            qty=100,
            avg_entry=50.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.45, "intact": False},
            lifecycle="ACTIVE",
            pnl_unrealized=10.0,
            metadata={"holding_days": 20.0, "trend_proxy": 0.2},
        )

        decision = self.dead_money.recommend_action(position, trend_proxy=0.2)
        self.assertEqual(decision.action, "ROTATE")
        self.assertTrue(decision.metadata.get("dead_money"))

    def test_winner_partial_protection(self):
        position = Position(
            symbol="WINNER1",
            qty=100,
            avg_entry=100.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.82, "intact": True},
            lifecycle="ACTIVE",
            pnl_unrealized=1200.0,
            metadata={"holding_days": 12.0, "trend_proxy": 0.55},
        )

        decision = self.protector.recommend_action(position, trend_proxy=0.55)
        self.assertEqual(decision.action, "PARTIAL_EXIT")
        self.assertGreaterEqual(decision.metadata.get("pnl_pct", 0.0), 0.08)

    def test_conviction_scaling_allowed(self):
        position = Position(
            symbol="SCALE1",
            qty=50,
            avg_entry=200.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.88, "intact": True},
            lifecycle="ACTIVE",
            pnl_unrealized=600.0,
            metadata={"holding_days": 7.0, "trend_proxy": 0.72, "add_count": 1},
        )

        decision = self.scaler.recommend_action(position, trend_proxy=0.72)
        self.assertEqual(decision.action, "BUY_MORE")
        self.assertGreater(decision.metadata.get("scale_factor", 0.0), 0.0)

    def test_loser_scaling_rejected(self):
        position = Position(
            symbol="LOSER1",
            qty=100,
            avg_entry=100.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.75, "intact": True},
            lifecycle="ACTIVE",
            pnl_unrealized=-150.0,
            metadata={"holding_days": 10.0, "trend_proxy": 0.75, "add_count": 0},
        )

        decision = self.scaler.recommend_action(position, trend_proxy=0.75)
        self.assertNotEqual(decision.action, "BUY_MORE")
        self.assertEqual(decision.action, "HOLD")


if __name__ == "__main__":
    unittest.main()
