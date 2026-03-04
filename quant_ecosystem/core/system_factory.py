from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.risk.risk_engine import RiskEngine
from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.strategy_bank.strategy_registry import StrategyRegistry
from quant_ecosystem.research.alpha_competition_engine import AlphaCompetitionEngine
from quant_ecosystem.evolution.alpha_evolution_engine import AlphaEvolutionEngine
from quant_ecosystem.core.capital.capital_intelligence_engine import CapitalIntelligenceEngine
from quant_ecosystem.broker.fyers_broker import FyersBroker


class SystemFactory:

    def __init__(self, config):
        self.config = config

    def build(self):

        # ---------- Broker ----------
        broker = FyersBroker(self.config)

        # ---------- Core Engines ----------
        risk_engine = RiskEngine(self.config)
        portfolio_engine = PortfolioEngine()

        # ---------- Strategy Layer ----------
        strategy_registry = StrategyRegistry()

        # ---------- Intelligence Engines ----------
        alpha_competition = AlphaCompetitionEngine(strategy_registry)
        alpha_evolution = AlphaEvolutionEngine(strategy_registry)
        capital_intelligence = CapitalIntelligenceEngine()

        # ---------- Execution Router ----------
        router = ExecutionRouter(
            broker=broker,
            risk_engine=risk_engine,
            portfolio_engine=portfolio_engine,
            state=None
        )

        # attach engines
        router.strategy_registry = strategy_registry
        router.alpha_competition = alpha_competition
        router.alpha_evolution = alpha_evolution
        router.capital_intelligence = capital_intelligence

        return router


def build_router(config):
    factory = SystemFactory(config)
    return factory.build()