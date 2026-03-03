from broker.broker_router import BrokerRouter
from broker.coinswitch_broker import CoinSwitchBroker
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
from quant_ecosystem.autonomous_controller.controller import AutonomousController
from quant_ecosystem.capital_allocator.layer import CapitalAllocatorLayer
from quant_ecosystem.capital_allocator.allocation_engine import CapitalAllocator
from quant_ecosystem.execution_router.layer import ExecutionRouterLayer
from quant_ecosystem.market_intelligence.layer import MarketIntelligenceLayer
from quant_ecosystem.market_regime import MarketRegimeDetector
from quant_ecosystem.mutation_engine.layer import MutationEngineLayer
from quant_ecosystem.risk_engine.layer import RiskEngineLayer
from quant_ecosystem.strategy_selector.selector_core import AutonomousStrategySelector
from quant_ecosystem.strategy_bank.layer import StrategyBankLayer
from risk.risk_engine import RiskEngine
from strategy_bank.engine.strategy_bank_engine import StrategyBankEngine
from strategy_bank.live_strategy_engine import LiveStrategyEngine
from strategy_bank.mutation.mutation_engine import MutationEngine
from strategy_bank.strategy_registry import StrategyRegistry


def build_router():
    config = Config()
    state = SystemState()
    state.trading_mode = config.mode.upper()
    state.capital_cap = state.initial_equity * config.capital_cap_multiplier

    broker_name = str(config.broker_name or "FYERS").upper().strip()
    if broker_name == "COINSWITCH":
        broker = CoinSwitchBroker()
    else:
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

    # Optional additive engines (no changes to execution/risk core flow).
    execution.strategy_bank_engine = StrategyBankEngine(config=config) if config.enable_strategy_bank else None
    execution.mutation_engine = MutationEngine(config=config) if config.enable_strategy_mutation else None
    execution.autonomous_controller = AutonomousController()
    execution.capital_allocator_layer = CapitalAllocatorLayer()
    execution.market_intelligence_layer = MarketIntelligenceLayer()
    execution.execution_layer = ExecutionRouterLayer(router=execution)
    execution.risk_layer = RiskEngineLayer(risk_engine=risk_engine)
    execution.strategy_bank_layer = StrategyBankLayer(bank_engine=execution.strategy_bank_engine)
    execution.mutation_layer = MutationEngineLayer(mutation_engine=execution.mutation_engine)
    execution.market_regime_detector = MarketRegimeDetector()
    execution.strategy_selector = AutonomousStrategySelector(
        strategy_bank_layer=execution.strategy_bank_layer,
        strategy_engine=strategy_engine,
        strategy_bank_engine=execution.strategy_bank_engine,
        regime_source=lambda: str(getattr(execution.autonomous_controller, "last_regime", "RANGE_BOUND")),
        max_active_strategies=5,
    )
    execution.capital_allocator_engine = CapitalAllocator(
        strategy_bank_layer=execution.strategy_bank_layer,
        strategy_selector=execution.strategy_selector,
    )
    execution.autonomous_controller.set_mode(execution, config.operation_mode)

    telegram = TelegramController()
    telegram.bind_router(execution)
    execution.telegram = telegram

    return execution
