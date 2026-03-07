import logging
import random
import time

logger = logging.getLogger(__name__)


class StrategyDiscoveryEngine:

    def __init__(self, router):
        self.router = router
        self.running = False

    def start(self):
        logger.info("Autonomous Strategy Discovery Engine started")
        self.running = True

        while self.running:
            try:
                self.discovery_cycle()
            except Exception as e:
                logger.exception(f"Discovery cycle failed: {e}")

            time.sleep(10)

    def stop(self):
        self.running = False

    def discovery_cycle(self):

        genome_lib = self.router.genome_library
        evaluator = getattr(self.router, "genome_evaluator", None)

        if not genome_lib or not evaluator:
            logger.warning("Genome system not ready")
            return

        # 1 generate genome
        genome = genome_lib.generate_random()

        # 2 mutate
        if random.random() < 0.5:
            genome = genome_lib.mutate(genome)

        # 3 evaluate
        result = evaluator.evaluate(genome)

        # 4 store results
        self.router.research_memory.record_evolved_alpha(
            genome_id=genome["id"],
            metrics=result
        )

        logger.info(
            f"Genome evaluated | fitness={result.get('fitness_score')}"
        )