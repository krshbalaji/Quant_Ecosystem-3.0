import logging
import random
import uuid
from quant_ecosystem.research.alpha_templates.structural_library import AlphaStructuralLibrary

logger = logging.getLogger(__name__)

def _new_id(self):
    return "arl_" + uuid.uuid4().hex[:8]

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
        self.structural_library = AlphaStructuralLibrary()
        self.config = config

        logger.info("StrategyDiscoveryEngine initialized")

    def _new_id(self, family: str) -> str:
        import time
        import uuid

        ts = time.strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]

        return f"arl_{family}_{ts}_{uid}"

    def _generate_random_genome(self):

        indicator = random.choice(self.INDICATORS)

        template = self.structural_library.sample_template()

        genome = {
            "id": self._new_id(template["family"]),
            "structure": template,
            "mutation_intensity": random.uniform(0.05, 0.25),
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