import unittest

from quant_ecosystem.contracts.position import Position
from quant_ecosystem.contracts.signal_intent import SignalIntent
from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.portfolio import recommend_rotation
from quant_ecosystem.portfolio.portfolio_snapshot import PortfolioSnapshot


class PortfolioRotationEngineTests(unittest.TestCase):

    def test_weak_holding_vs_superior_candidate_recommends_rotate(self):
        held = Position(
            symbol="SBIN",
            qty=100,
            avg_entry=120.0,
            profile=ProfileTypes.SWING,
            thesis={"confidence": 0.38, "intact": False},
            lifecycle="ACTIVE",
            pnl_unrealized=-60.0,
            metadata={"holding_days": 16.0, "trend_proxy": 0.22},
        )

        candidate = SignalIntent.from_mapping(
            {
                "symbol": "XAU",
                "side": "BUY",
                "profile": ProfileTypes.FNO,
                "strategy": "PRECISION",
                "confidence": 0.92,
                "metadata": {"score": 93, "notional": 12000.0},
            }
        )

        snapshot = PortfolioSnapshot.from_positions([held])
        decisions = recommend_rotation(snapshot, [candidate], trend_proxy_map={"SBIN": 0.22})

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].action, "ROTATE")
        self.assertEqual(decisions[0].symbol, "SBIN")
        self.assertIn("superior candidate", decisions[0].reason)


if __name__ == "__main__":
    unittest.main()
