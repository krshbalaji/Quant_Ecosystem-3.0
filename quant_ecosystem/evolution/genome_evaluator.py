import random
import logging

logger = logging.getLogger(__name__)


class GenomeEvaluator:

    def __init__(self, router=None):

        self.router = router

    def evaluate(self, genome):

        sharpe = random.uniform(-1.0, 2.0)
        drawdown = random.uniform(0, 0.5)

        fitness = sharpe - drawdown

        result = {
            "fitness_score": fitness,
            "sharpe": sharpe,
            "drawdown": drawdown
        }

        logger.info(
            f"Genome evaluated | fitness={fitness:.3f}"
        )

        return result