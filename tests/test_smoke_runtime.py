import unittest

from broker.broker_router import BrokerRouter
from broker.fyers_broker import FyersBroker
from broker.reconciliation.broker_reconciler import BrokerReconciler
from core.capital.capital_governance_engine import CapitalGovernanceEngine
from core.system_state import SystemState
from execution.execution_router import ExecutionRouter
from market.market_data_engine import MarketDataEngine
from portfolio.portfolio_engine import PortfolioEngine
from portfolio.position_sizer import PositionSizer
from risk.risk_engine import RiskEngine
from strategy_bank.live_strategy_engine import LiveStrategyEngine
from strategy_bank.strategy_registry import StrategyRegistry


class SmokeRuntimeTests(unittest.TestCase):

    def test_fyers_broker_snapshot_contract(self):
        broker = FyersBroker()
        broker.connect()

        order = broker.place_order(
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=1,
            price=100.0,
            fee=0.0,
            meta={"test": True},
        )
        self.assertEqual(order["status"], "FILLED")

        snapshot = broker.get_account_snapshot(latest_prices={"NSE:SBIN-EQ": 101.0})
        expected = {
            "cash_balance",
            "realized_pnl",
            "unrealized_pnl",
            "fees_paid",
            "equity",
            "orders",
            "tradebook",
            "positions",
            "account_source",
        }
        self.assertTrue(expected.issubset(set(snapshot.keys())))
        self.assertIsInstance(snapshot["positions"], list)
        self.assertGreaterEqual(len(snapshot["orders"]), 1)

    def test_execution_router_one_cycle_no_crash(self):
        state = SystemState()
        broker = FyersBroker()
        broker.connect()
        broker_router = BrokerRouter(broker)
        portfolio_engine = PortfolioEngine()
        reconciler = BrokerReconciler(
            broker_router=broker_router,
            portfolio_engine=portfolio_engine,
            state=state,
        )

        router = ExecutionRouter(
            broker=broker_router,
            risk_engine=RiskEngine(),
            state=state,
            market_data=MarketDataEngine(),
            strategy_engine=LiveStrategyEngine(strategy_registry=StrategyRegistry()),
            portfolio_engine=portfolio_engine,
            reconciler=reconciler,
            capital_governance=CapitalGovernanceEngine(),
            position_sizer=PositionSizer(),
            symbols=["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:INFY-EQ"],
            outcome_memory=None,
        )

        result = router.run_cycle(regime="MEAN_REVERSION")
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn(result["status"], {"TRADE", "SKIP"})


if __name__ == "__main__":
    unittest.main()
