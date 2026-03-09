import random
import uuid
import time

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:

    def __init__(self, market_data=None, factor_library=None, config=None, **kwargs):
        self.market_data = market_data
        self.factor_library = factor_library
        self.config = config

        logger.info("StrategyDiscoveryEngine initialized")

    def start(self):

        logger.info("Autonomous Strategy Discovery Engine started")

        while True:

            try:

                strategies = self.discover()

                if self.research_grid:

                    logger.info("Submitting strategies to ResearchGrid")

                    self.research_grid.submit_genome_sweep(
                        strategies,
                        symbols=["NSE:SBIN", "NSE:RELIANCE", "NSE:TCS"]
                    )

                time.sleep(60)

            except Exception as e:

                logger.warning(f"Discovery loop error: {e}")
                time.sleep(10)
                
    def discover(self, count=20, symbols=None, wait=False):
        """
        Generate strategy genomes for evaluation.

        Compatible with AutonomousResearchLoop which calls discover(count=...)
        """
        genomes = []

        try:
            for _ in range(count):

                genome = {
                    "genome_id": f"arl_{self._random_family()}_{self._timestamp()}",
                    "family": self._random_family(),
                    "parameters": self._generate_parameters()
                }

                genomes.append(genome)

        except Exception as e:
            logger.warning(f"Strategy discovery failed: {e}")

        return genomes
    
    import random
    import time


    def _random_family(self):
        families = [
            "momentum",
            "mean_reversion",
            "breakout",
            "volatility",
            "trend",
        ]
        return random.choice(families)


    def _timestamp(self):
        return time.strftime("%Y%m%d_%H%M%S")


    def _generate_parameters(self):

        return {
            "lookback": random.randint(5, 50),
            "threshold": round(random.uniform(0.5, 3.0), 2),
            "exit": round(random.uniform(0.5, 2.0), 2),
        }
    
    # -------------------------------------------------

    def generate(self):

        new_strategies = []

        for _ in range(self.max_new_strategies):

            strategy = self._generate_strategy()

            if strategy:
                self.registry.register(strategy)
                new_strategies.append(strategy)

        return new_strategies

    # -------------------------------------------------

    def _generate_strategy(self):

        feature = random.choice([
            "rsi",
            "momentum",
            "volatility",
            "atr",
            "vwap"
        ])

        threshold = random.uniform(20, 80)

        strategy_id = f"generated_{uuid.uuid4().hex[:8]}"

        return GeneratedStrategy(
            strategy_id,
            feature,
            threshold
        )