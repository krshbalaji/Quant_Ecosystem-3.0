import threading
import time
import logging

logger = logging.getLogger(__name__)


class ResearchDaemon:

    def __init__(self, router):
        self.router = router
        self.running = False

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()

    def _loop(self):

        logger.info("ResearchDaemon started")

        while self.running:

            try:

                discovery = getattr(self.router, "strategy_discovery", None)
                grid = getattr(self.router, "research_grid", None)

                if discovery and grid:

                    genomes = discovery.generate_candidates(10)

                    grid.submit_genome_sweep(
                        genomes,
                        symbols=self.router.symbols
                    )

            except Exception as e:
                logger.warning(f"ResearchDaemon error: {e}")

            time.sleep(30)