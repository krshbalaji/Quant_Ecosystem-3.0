from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.risk.risk_engine import RiskEngine
from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.core.strategy_registry import StrategyRegistry
from quant_ecosystem.research.alpha_competition_engine import AlphaCompetitionEngine
from quant_ecosystem.evolution.alpha_evolution_engine import AlphaEvolutionEngine
from quant_ecosystem.core.capital.capital_intelligence_engine import CapitalIntelligenceEngine
from quant_ecosystem.core.system_state import SystemState
from quant_ecosystem.broker.fyers_broker import FyersBroker
from quant_ecosystem.market.market_data_engine import MarketDataEngine
from quant_ecosystem.market_pulse.pulse_engine import MarketPulseEngine
from quant_ecosystem.research.strategy_discovery_engine import StrategyDiscoveryEngine
from quant_ecosystem.research.distributed_research_engine import DistributedResearchEngine

class System:
    """
    Lightweight system container used by MasterOrchestrator.
    All engines are attached as attributes on this object.
    """

    pass


class SystemFactory:

    def __init__(self, config):
        self.config = config

    def build(self):
        """
        Build and wire the core trading system.
        Returns the ExecutionRouter, with all engines also attached
        to a lightweight System container accessible via router.system.
        """
        from quant_ecosystem.research.alpha_discovery_engine import AlphaDiscoveryEngine
        from quant_ecosystem.evolution.alpha_factory import AlphaFactory
        from quant_ecosystem.evolution.distributed_alpha_grid import DistributedAlphaGrid

        # System container
        system = System()

        # 1) Broker
        broker = FyersBroker(config=self.config)
        broker.connect()

        # 2) State
        state = SystemState()

        distributed_engine = DistributedResearchEngine(market_data)

        system.distributed_research = distributed_engine
        
        # 3) Strategy registry
        strategy_registry = StrategyRegistry()

        discovery = StrategyDiscoveryEngine(
            market_data,
            strategy_registry
        )

        system.strategy_discovery = discovery

        # Institutional strategy universe
        from quant_ecosystem.strategy_bank.strategy_universe import StrategyUniverse

        universe = StrategyUniverse()
        universe.load_strategies(strategy_registry)

        # 4) Portfolio engine
        portfolio_engine = PortfolioEngine()

        # 5) Risk engine
        risk_engine = RiskEngine(config=self.config)

        # 6) Market data engine
        market_data = MarketDataEngine(
            broker=broker,
            symbols=["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"],
            universe_manager=None,
            timeframe="5m",
        )

        # Attach feature engine on top of market data
        from quant_ecosystem.intelligence.feature_engine import FeatureEngine

        feature_engine = FeatureEngine(market_data)
        setattr(market_data, "feature_engine", feature_engine)

        # 7) Market pulse engine
        market_pulse = MarketPulseEngine(market_data_engine=market_data)

        # 8) Execution router (core trading engine)
        router = ExecutionRouter(
            broker=broker,
            risk_engine=risk_engine,
            state=state,
            market_data=market_data,
            portfolio_engine=portfolio_engine,
        )

        # 9) Research / discovery engines
        from quant_ecosystem.research.performance_store import PerformanceStore
        from quant_ecosystem.research.performance_attribution import PerformanceAttributionEngine

        performance_store = PerformanceStore()
        perf_attribution = PerformanceAttributionEngine(performance_store)
        alpha_discovery = AlphaDiscoveryEngine(strategy_registry)
        alpha_factory = AlphaFactory(strategy_registry)
        alpha_grid = DistributedAlphaGrid(alpha_factory)
        alpha_competition = AlphaCompetitionEngine(strategy_registry, performance_store=performance_store)
        alpha_evolution = AlphaEvolutionEngine(strategy_registry)

        # 10) Capital intelligence and allocation engines
        capital_intelligence = CapitalIntelligenceEngine(
            portfolio_engine=portfolio_engine,
            risk_engine=risk_engine,
        )

        from quant_ecosystem.portfolio.capital_allocator import CapitalAllocator
        from quant_ecosystem.portfolio.portfolio_constructor import PortfolioConstructor
        from quant_ecosystem.risk.risk_overlay_engine import RiskOverlayEngine
        from quant_ecosystem.execution.execution_planner import ExecutionPlanner
        from quant_ecosystem.signals.signal_engine import SignalEngine
        from quant_ecosystem.signals.signal_aggregator import SignalAggregator

        capital_allocator = CapitalAllocator()
        portfolio_constructor = PortfolioConstructor(capital_allocator)
        risk_overlay = RiskOverlayEngine(risk_engine, portfolio_engine, state)
        execution_planner = ExecutionPlanner(portfolio_engine, state, market_data)
        signal_engine = SignalEngine(strategy_registry, market_data)
        signal_aggregator = SignalAggregator()

        # Attach engines to the system container (for MasterOrchestrator)
        system.broker = broker
        system.state = state
        system.strategy_registry = strategy_registry
        system.portfolio_engine = portfolio_engine
        system.risk_engine = risk_engine
        system.market_data = market_data
        system.feature_engine = feature_engine
        system.market_pulse = market_pulse
        system.execution_router = router
        system.alpha_discovery = alpha_discovery
        system.alpha_factory = alpha_factory
        system.alpha_grid = alpha_grid
        system.alpha_competition = alpha_competition
        system.alpha_evolution = alpha_evolution
        system.capital_intelligence = capital_intelligence
        system.performance_store = performance_store
        system.capital_allocator = capital_allocator
        system.strategy_universe = universe
        system.performance_attribution = perf_attribution
        system.portfolio_constructor = portfolio_constructor
        system.risk_overlay = risk_overlay
        system.execution_planner = execution_planner
        system.signal_engine = signal_engine
        system.signal_aggregator = signal_aggregator

        # Attach engines to the execution router for backwards compatibility
        router.system = system
        router.strategy_registry = strategy_registry
        router.alpha_competition = alpha_competition
        router.alpha_evolution = alpha_evolution
        router.capital_intelligence = capital_intelligence
        router.alpha_discovery = alpha_discovery
        router.alpha_factory = alpha_factory
        router.alpha_grid = alpha_grid
        router.state = state
        router.portfolio_engine = portfolio_engine
        router.risk_engine = risk_engine
        router.market_data = market_data
        router.broker = broker

        return router


def build_router(config):
    factory = SystemFactory(config)
    return factory.build()