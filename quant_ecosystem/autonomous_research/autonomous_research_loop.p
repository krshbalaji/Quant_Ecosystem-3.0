import threading
import time
import logging

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:

    def __init__(
        self,
        discovery_engine=None,
        mutation_engine=None,
        evolution_engine=None,
        research_grid=None,
        genome_library=None,
        meta_research_ai=None,
        interval_sec=120,
    ):
        self.discovery_engine = discovery_engine
        self.mutation_engine = mutation_engine
        self.evolution_engine = evolution_engine
        self.research_grid = research_grid
        self.genome_library = genome_library
        self.meta_research_ai = meta_research_ai

        self.interval = interval_sec
        self._thread = None
        self._running = False
        self._cycle = 0

        logger.info(
            "[research_loop] constructed | interval=%ss engines=%s",
            interval_sec,
            {
                "discovery": bool(discovery_engine),
                "mutation": bool(mutation_engine),
                "evolution": bool(evolution_engine),
                "grid": bool(research_grid),
                "bank": bool(genome_library),
            },
        )

    def start(self):

        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )

        self._thread.start()

        logger.info("[research_loop] daemon thread started")

    def stop(self):

        self._running = False

    def _run_loop(self):

        logger.info("[research_loop] research loop entering main cycle")

        while self._running:

            self._cycle += 1

            logger.info(
                "[research_loop] ---- cycle #%s started ----",
                self._cycle
            )

            try:

                genomes = []

                if self.discovery_engine:
                    logger.info("[research_loop] discovering strategies")
                    genomes = self.discovery_engine.discover()

                if self.mutation_engine:
                    logger.info("[research_loop] mutating genomes")
                    genomes += self.mutation_engine.mutate(genomes)

                if self.evolution_engine:
                    logger.info("[research_loop] evolving population")
                    genomes += self.evolution_engine.evolve(genomes)

                if self.research_grid:
                    logger.info("[research_loop] submitting genomes to research grid")
                    results = self.research_grid.submit_genome_sweep(genomes)

                    logger.info(
                        "[research_loop] evaluation complete | %s genomes",
                        len(results),
                    )

                if self.meta_research_ai:
                    logger.info("[research_loop] updating MetaResearchAI")
                    self.meta_research_ai.force_refresh()

            except Exception as e:

                logger.exception(
                    "[research_loop] cycle error: %s",
                    e
                )

            time.sleep(self.interval)