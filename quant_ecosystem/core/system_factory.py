import logging

from quant_ecosystem.market.market_data_engine import MarketDataEngine
from quant_ecosystem.market.market_universe_manager import MarketUniverseManager

from quant_ecosystem.research.distributed_research_engine import DistributedResearchEngine
from quant_ecosystem.research.strategy_discovery_engine import StrategyDiscoveryEngine
from quant_ecosystem.research.strategy_mutation_engine import StrategyMutationEngine
from quant_ecosystem.research.research_dataset_builder import ResearchDatasetBuilder
from quant_ecosystem.research.factor_dataset_builder import FactorDatasetBuilder

from quant_ecosystem.evolution.alpha_evolution_engine import AlphaEvolutionEngine

from quant_ecosystem.execution.execution_router import ExecutionRouter
from quant_ecosystem.execution.broker_router import BrokerRouter

from quant_ecosystem.portfolio.capital_intelligence_engine import CapitalIntelligenceEngine


logger = logging.getLogger(__name__)


class SystemFactory:
    """
    Central wiring factory for the entire Quant Ecosystem.
    Builds and connects all system components.
    """

    def __init__(self, config):
        self.config = config

    def build(self):

        logger.info("Initializing market universe...")
        universe = MarketUniverseManager(self.config)

        logger.info("Initializing market data engine...")
        market_data = MarketDataEngine(self.config, universe)

        logger.info("Initializing research dataset builder...")
        dataset_builder = ResearchDatasetBuilder(market_data)

        logger.info("Initializing factor dataset builder...")
        factor_builder = FactorDatasetBuilder(dataset_builder)

        logger.info("Initializing distributed research engine...")
        distributed_engine = DistributedResearchEngine()

        logger.info("Initializing strategy discovery engine...")
        discovery_engine = StrategyDiscoveryEngine(
            dataset_builder,
            factor_builder,
            distributed_engine
        )

        logger.info("Initializing strategy mutation engine...")
        mutation_engine = StrategyMutationEngine()

        logger.info("Initializing alpha evolution engine...")
        evolution_engine = AlphaEvolutionEngine(
            discovery_engine,
            mutation_engine
        )

        logger.info("Initializing capital intelligence engine...")
        capital_intelligence = CapitalIntelligenceEngine(self.config)

        logger.info("Initializing broker router...")
        broker_router = BrokerRouter(self.config)

        logger.info("Initializing execution router...")
        execution_router = ExecutionRouter(
            broker_router,
            capital_intelligence
        )

        logger.info("System components successfully wired.")

        return {
            "market_data": market_data,
            "dataset_builder": dataset_builder,
            "factor_builder": factor_builder,
            "distributed_research": distributed_engine,
            "strategy_discovery": discovery_engine,
            "strategy_mutation": mutation_engine,
            "alpha_evolution": evolution_engine,
            "capital_intelligence": capital_intelligence,
            "execution_router": execution_router,
        }


def build_router(config):
    """
    Public entry point used by main.py
    """
    factory = SystemFactory(config)
    return factory.build()