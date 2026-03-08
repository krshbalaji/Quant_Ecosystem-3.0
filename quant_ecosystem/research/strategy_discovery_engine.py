import logging
import random
import uuid

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:
    """
    Generates new candidate strategy genomes.
    Used by AutonomousResearchLoop.
    """

    INDICATORS = [
        "momentum",
        "rsi",
        "ma_cross",
        "breakout",
        "mean_reversion",
        "volatility_breakout",
    ]

    def __init__(self, market_data=None, factor_library=None, config=None, **kwargs):
        self.market_data = market_data
        self.factor_library = factor_library
        self.config = config

        logger.info("StrategyDiscoveryEngine initialized")

    def _generate_random_genome(self):

        indicator = random.choice(self.INDICATORS)

        genome = {
            "genome_id": f"arl_{indicator}_{uuid.uuid4().hex[:8]}",
            "signal_gene": {
                "indicator": indicator,
                "lookback": random.randint(5, 50),
                "threshold": round(random.uniform(0.1, 2.0), 2),
            },
        }

        return genome

    def discover(self, count=20, symbols=None, **kwargs):
        """
        Generate new random strategy genomes.
        """

        genomes = []

        for _ in range(count):
            genome = self._generate_random_genome()
            genomes.append(genome)

        logger.info("StrategyDiscoveryEngine generated %d genomes", len(genomes))

        return genomes