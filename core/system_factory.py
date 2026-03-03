from broker.broker_router import BrokerRouter
from broker.fyers_broker import FyersBroker
from broker.reconciliation.broker_reconciler import BrokerReconciler
from control.telegram_controller import TelegramController
from core.capital.capital_governance_engine import CapitalGovernanceEngine
from core.config_loader import Config
from core.persistence.outcome_memory import OutcomeMemory
from core.system_state import SystemState
from execution.execution_router import ExecutionRouter
from market.market_data_engine import MarketDataEngine
from portfolio.portfolio_engine import PortfolioEngine
from portfolio.position_sizer import PositionSizer
from risk.risk_engine import RiskEngine
from strategy_bank.live_strategy_engine import LiveStrategyEngine
from strategy_bank.strategy_registry import StrategyRegistry


def build_router():
    config = Config()
    state = SystemState()
    state.trading_mode = config.mode.upper()
    state.capital_cap = state.initial_equity * config.capital_cap_multiplier

    broker = FyersBroker()
    broker.connect()
    broker_router = BrokerRouter(broker)

    risk_engine = RiskEngine()
    market_data = MarketDataEngine()
    portfolio_engine = PortfolioEngine()
    capital_governance = CapitalGovernanceEngine()
    position_sizer = PositionSizer()
    strategy_registry = StrategyRegistry()
    strategy_engine = LiveStrategyEngine(strategy_registry=strategy_registry)
    outcome_memory = OutcomeMemory()
    reconciler = BrokerReconciler(
        broker_router=broker_router,
        portfolio_engine=portfolio_engine,
        state=state,
    )

    execution = ExecutionRouter(
        broker=broker_router,
        risk_engine=risk_engine,
        state=state,
        market_data=market_data,
        strategy_engine=strategy_engine,
        portfolio_engine=portfolio_engine,
        reconciler=reconciler,
        capital_governance=capital_governance,
        position_sizer=position_sizer,
        symbols=config.trade_symbols,
        outcome_memory=outcome_memory,
    )
    execution.survival_mode = "NORMAL"

    telegram = TelegramController()
    telegram.bind_router(execution)
    execution.telegram = telegram

    return execution
