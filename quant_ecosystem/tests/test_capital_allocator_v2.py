import unittest

from quant_ecosystem.contracts.profile_types import ProfileTypes
from quant_ecosystem.risk.capital_allocator_v2 import CapitalAllocatorV2
from quant_ecosystem.risk.correlation_guard import CorrelationGuard
from quant_ecosystem.risk.reserve_manager import ReserveManager


class CapitalAllocatorV2Tests(unittest.TestCase):

    def test_default_bucket_allocation(self):
        allocator = CapitalAllocatorV2(total_capital=100_000.0)

        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.SCALP), 10_000.0)
        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.INTRADAY), 20_000.0)
        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.SWING), 20_000.0)
        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.FNO), 10_000.0)
        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.MULTIBAGGER), 25_000.0)
        self.assertAlmostEqual(allocator.get_bucket_size(ProfileTypes.INVESTMENT), 15_000.0)

    def test_can_allocate_and_consume(self):
        allocator = CapitalAllocatorV2(total_capital=100_000.0)

        self.assertTrue(allocator.can_allocate(ProfileTypes.SCALP, 5_000.0))
        self.assertTrue(allocator.consume_budget(ProfileTypes.SCALP, 5_000.0))
        self.assertAlmostEqual(allocator.get_available_budget(ProfileTypes.SCALP), 5_000.0)
        self.assertFalse(allocator.can_allocate(ProfileTypes.SCALP, 6_000.0))

        allocator.release_budget(ProfileTypes.SCALP, 2_000.0)
        self.assertAlmostEqual(allocator.get_available_budget(ProfileTypes.SCALP), 7_000.0)

    def test_reserve_manager_blocks_without_unlock(self):
        allocator = CapitalAllocatorV2(total_capital=100_000.0, reserve_pct=0.05)

        self.assertAlmostEqual(allocator.reserve_manager.reserve_amount, 5_000.0)
        self.assertFalse(allocator.reserve_manager.can_consume(ProfileTypes.SCALP, 1_000.0))

        self.assertTrue(allocator.unlock_reserve_for_premium("A+ opportunity"))
        self.assertTrue(allocator.reserve_manager.can_consume(ProfileTypes.SCALP, 1_000.0))
        self.assertTrue(allocator.reserve_manager.consume(1_000.0))
        self.assertAlmostEqual(allocator.reserve_manager.available, 4_000.0)

    def test_correlation_guard_rejects_same_thesis(self):
        guard = CorrelationGuard(total_capital=100_000.0, max_thesis_exposure_pct=0.20)

        allowed, _ = guard.evaluate("BTC_SHORT", 10_000.0, group="SHORT")
        self.assertTrue(allowed)

        guard.record_exposure("BTC_SHORT", 10_000.0, group="SHORT")
        allowed, reason = guard.evaluate("BTC_SHORT", 11_000.0, group="SHORT")
        self.assertFalse(allowed)
        self.assertIn("same thesis exposure too high", reason)

    def test_correlation_guard_rejects_group_limit(self):
        guard = CorrelationGuard(total_capital=100_000.0, max_group_exposures=2)

        guard.record_exposure("BTC_SHORT", 5_000.0, group="SHORT")
        guard.record_exposure("ETH_SHORT", 5_000.0, group="SHORT")

        allowed, reason = guard.evaluate("SOL_SHORT", 1_000.0, group="SHORT")
        self.assertFalse(allowed)
        self.assertIn("duplicate thesis group exposure limit reached", reason)

    def test_reserve_manager_release(self):
        manager = ReserveManager(total_capital=100_000.0, reserve_pct=0.05)
        self.assertEqual(manager.available, 5_000.0)

        manager.unlock_for_premium("unlock")
        self.assertTrue(manager.consume(2_000.0))
        manager.release(1_000.0)
        self.assertAlmostEqual(manager.available, 4_000.0)


if __name__ == "__main__":
    unittest.main()
