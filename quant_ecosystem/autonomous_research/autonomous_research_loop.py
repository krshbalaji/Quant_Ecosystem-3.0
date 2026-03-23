import threading
import time
import logging

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:

    def __init__(
        self,
        resolution: str,
        research_grid,
        discovery_engine=None,
        mutation_engine=None,
        evolution_engine=None,
        meta_research_ai=None,
        router=None,
        interval=120,
        startup_delay=5,
    ):

        self.resolution = resolution
        self.grid = research_grid
        self.discovery_engine = discovery_engine
        self.mutation_engine = mutation_engine
        self.evolution_engine = evolution_engine
        self.meta_ai = meta_research_ai
        self.router = router

        self.interval = interval
        self.startup_delay = startup_delay

        self._running = False
        self._thread = None
        self._cycle = 0

        logger.info(
            f"[research_loop] init | resolution={resolution} interval={interval}"
        )

    # --------------------------------------------------------

    def start(self):

        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )

        self._thread.start()

        logger.info(
            f"[research_loop] daemon thread started (interval={self.interval}s startup_delay={self.startup_delay}s)"
        )

    # --------------------------------------------------------

    def _run_loop(self):

        logger.info(
            f"[research_loop] startup delay {self.startup_delay}s …"
        )

        time.sleep(self.startup_delay)

        logger.info(
            "[research_loop] research loop is live — first cycle starting now"
        )

        while self._running:

            self._cycle += 1

            logger.info(
                f"[research_loop] ---- cycle #{self._cycle} started ----"
            )

            try:
                self._run_cycle()

            except Exception as e:
                logger.exception(
                    f"[research_loop] cycle failure: {e}"
                )

            time.sleep(self.interval)

    # --------------------------------------------------------

    def _run_cycle(self):

        # 1 DISCOVERY
        genomes = []

        if self.discovery_engine:
            genomes = self.discovery_engine.discover(
                resolution=self.resolution
            )

        # fallback safety
        if not genomes:
            logger.info("[research_loop] discovery fallback — empty batch")
            return

        # 2 MUTATION
        if self.mutation_engine:
            genomes += self.mutation_engine.mutate(genomes)

        # 3 EVOLUTION
        if self.evolution_engine:
            genomes = self.evolution_engine.evolve(genomes)

        # 4 SUBMIT GRID
        self.grid.submit_genome_sweep(
            genomes=genomes,
            resolution=self.resolution
        )

        # 5 META FEEDBACK
        if self.meta_ai:
            self.meta_ai.observe_cycle(
                resolution=self.resolution,
                batch_size=len(genomes)
            )