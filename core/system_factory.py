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
from quant_ecosystem.alpha_scanner import GlobalAlphaScanner, MarketDataAdapter
from quant_ecosystem.capital_allocator.layer import CapitalAllocatorLayer
from quant_ecosystem.capital_allocator.allocation_engine import CapitalAllocator
from quant_ecosystem.execution_router.layer import ExecutionRouterLayer
from quant_ecosystem.execution_intelligence import ExecutionBrain
from quant_ecosystem.market_intelligence.layer import MarketIntelligenceLayer
from quant_ecosystem.market_regime import MarketRegimeDetector
from quant_ecosystem.microstructure import MicrostructureSimulator, SlippageModel, SpreadModel
from quant_ecosystem.regime_ai import AdaptiveRegimeEngine
from quant_ecosystem.meta_strategy import MetaStrategyBrain
from quant_ecosystem.mutation_engine.layer import MutationEngineLayer
from quant_ecosystem.portfolio_ai import PortfolioAI
from quant_ecosystem.risk_engine.layer import RiskEngineLayer
from quant_ecosystem.strategy_diversity import StrategyDiversityEngine
from quant_ecosystem.strategy_lab import BacktestEngine as StrategyLabBacktestEngine
from quant_ecosystem.strategy_lab import StrategyLabController
from quant_ecosystem.strategy_survival import StrategySurvivalEngine
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
    execution.meta_strategy_brain = (
        MetaStrategyBrain(
            strategy_bank_layer=execution.strategy_bank_layer,
            capital_allocator_engine=execution.capital_allocator_engine,
            mutation_layer=execution.mutation_layer,
            strategy_selector=execution.strategy_selector,
        )
        if config.enable_meta_strategy_brain
        else None
    )
    execution.strategy_lab_controller = (
        StrategyLabController(
            strategy_bank_layer=execution.strategy_bank_layer,
            mutation_layer=execution.mutation_layer,
            meta_strategy_brain=execution.meta_strategy_brain,
            sandbox_mode=bool(getattr(config, "strategy_lab_sandbox", True)),
        )
        if (config.enable_strategy_lab or config.enable_alpha_scanner)
        else None
    )
    execution.alpha_scanner = (
        GlobalAlphaScanner(
            strategy_lab_controller=execution.strategy_lab_controller,
            strategy_bank_layer=execution.strategy_bank_layer,
            meta_strategy_brain=execution.meta_strategy_brain,
            market_data_adapter=MarketDataAdapter(
                market_data_engine=market_data,
                broker_router=broker_router,
                max_concurrency=96,
            ),
            cycle_interval_sec=max(60, int(getattr(config, "alpha_scanner_interval_sec", 180))),
            max_assets_per_cycle=max(100, int(getattr(config, "alpha_scanner_max_assets", 1200))),
        )
        if config.enable_alpha_scanner
        else None
    )
    execution.regime_ai_engine = (
        AdaptiveRegimeEngine(
            model_path=getattr(config, "regime_ai_model_path", "quant_ecosystem/regime_ai/models/regime_model.pkl"),
            min_confidence=float(getattr(config, "regime_ai_min_confidence", 0.45)),
            rule_detector=execution.market_regime_detector,
        )
        if config.enable_regime_ai
        else None
    )
    execution.portfolio_ai_engine = (
        PortfolioAI(
            strategy_bank_layer=execution.strategy_bank_layer,
            capital_allocator_engine=execution.capital_allocator_engine,
            strategy_selector=execution.strategy_selector,
            meta_strategy_brain=execution.meta_strategy_brain,
            risk_engine=risk_engine,
        )
        if config.enable_portfolio_ai
        else None
    )
    execution.strategy_diversity_engine = (
        StrategyDiversityEngine(
            max_strategies_per_category=max(1, int(getattr(config, "strategy_diversity_max_per_category", 3))),
            max_correlation=float(getattr(config, "strategy_diversity_max_correlation", 0.75)),
            max_per_asset_class=max(1, int(getattr(config, "strategy_diversity_max_per_asset_class", 4))),
            max_per_timeframe=max(1, int(getattr(config, "strategy_diversity_max_per_timeframe", 4))),
        )
        if bool(getattr(config, "enable_strategy_diversity", False))
        else None
    )
    execution.strategy_survival_engine = (
        StrategySurvivalEngine(
            strategy_bank_layer=execution.strategy_bank_layer,
            meta_strategy_brain=execution.meta_strategy_brain,
            portfolio_ai=execution.portfolio_ai_engine,
            strategy_lab_controller=execution.strategy_lab_controller,
        )
        if bool(getattr(config, "enable_strategy_survival", False))
        else None
    )
    execution.microstructure_simulator = (
        MicrostructureSimulator(
            spread_model=SpreadModel(multiplier=float(getattr(config, "microstructure_spread_multiplier", 1.0))),
            slippage_model=SlippageModel(multiplier=float(getattr(config, "microstructure_slippage_multiplier", 1.0))),
            base_delay_ms=float(getattr(config, "microstructure_base_delay_ms", 120.0)),
        )
        if bool(getattr(config, "enable_microstructure_simulation", False))
        else None
    )
    execution.execution_brain = (
        ExecutionBrain(microstructure_simulator=execution.microstructure_simulator)
        if config.enable_execution_intelligence
        else None
    )
    if execution.strategy_lab_controller and execution.microstructure_simulator:
        execution.strategy_lab_controller.backtest_engine = StrategyLabBacktestEngine(
            microstructure_simulator=execution.microstructure_simulator
        )
    execution.autonomous_controller.set_mode(execution, config.operation_mode)

    telegram = TelegramController()
    telegram.bind_router(execution)
    execution.telegram = telegram

    return execution
