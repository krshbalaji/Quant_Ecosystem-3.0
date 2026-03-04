from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.risk.risk_engine import RiskEngine
from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.core.strategy_registry import StrategyRegistry
from quant_ecosystem.research.alpha_competition_engine import AlphaCompetitionEngine
from quant_ecosystem.evolution.alpha_evolution_engine import AlphaEvolutionEngine
from quant_ecosystem.core.capital.capital_intelligence_engine import CapitalIntelligenceEngine
from quant_ecosystem.core.system_state import SystemState
from quant_ecosystem.broker.fyers_broker import FyersBroker


class SystemFactory:

    def __init__(self, config):
        self.config = config

    def build(self):

        # Build core system components in canonical order.

        # 1) Broker
        broker = FyersBroker(config=self.config)

        # 2) State
        state = SystemState()

        # 3) Strategy registry
        strategy_registry = StrategyRegistry()

        # 4) Portfolio engine
        portfolio_engine = PortfolioEngine()

        # 5) Risk engine
        risk_engine = RiskEngine(config=self.config)

        # 6) Execution router (core trading engine)
        router = ExecutionRouter(
            broker=broker,
            risk_engine=risk_engine,
            state=state,
            portfolio_engine=portfolio_engine,
        )

        # 7) Research / alpha competition engine
        alpha_competition = AlphaCompetitionEngine(strategy_registry)

        # 8) Evolution engine
        alpha_evolution = AlphaEvolutionEngine(strategy_registry)

        # 9) Capital intelligence engine
        capital_intelligence = CapitalIntelligenceEngine(
            portfolio_engine=portfolio_engine,
            risk_engine=risk_engine,
        )

        # Attach engines to the system so the MasterOrchestrator
        # can access everything via self.system
        router.strategy_registry = strategy_registry
        router.alpha_competition = alpha_competition
        router.alpha_evolution = alpha_evolution
        router.capital_intelligence = capital_intelligence
        router.state = state
        router.portfolio_engine = portfolio_engine
        router.risk_engine = risk_engine
        router.broker = broker

        return router


def build_router(config):
    factory = SystemFactory(config)
    return factory.build()