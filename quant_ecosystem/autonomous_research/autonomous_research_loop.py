import threading
import time
import logging
import random

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:
    """
    Institutional Alpha Organism.

    Responsibilities:
    - discover genomes
    - regime aware mutation
    - multi symbol evaluation
    - submit to ResearchGrid
    """

    def __init__(
        self,
        resolution: str,
        research_grid=None,
        discovery_engine=None,
        mutation_engine=None,
        regime_memory=None,
        promotion_engine=None,
        multi_symbol_engine=None,
        sleep_interval=5,
    ):
        self.resolution = resolution

        self.grid = research_grid
        self.discovery = discovery_engine
        self.mutation = mutation_engine
        self.regime_memory = regime_memory
        self.promotion_engine = promotion_engine
        self.multi_symbol_engine = multi_symbol_engine

        self.sleep_interval = sleep_interval

        self._running = False
        self._thread = None

        logger.info(
            "[research_loop] organism created | resolution=%s",
            resolution
        )

    # -------------------------------------------------------

    def start(self):
        if self._running:
            return

        self._running = True

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"ResearchLoop-{self.resolution}"
        )
        self._thread.start()

        logger.info(
            "[research_loop] daemon started | resolution=%s",
            self.resolution
        )

    # -------------------------------------------------------

    def stop(self):
        self._running = False

    # -------------------------------------------------------

    def _run_loop(self):

        while self._running:

            try:

                # 1️⃣ Discover genome
                genome = None
                if self.discovery:
                    genome = self.discovery.discover()

                if genome is None:
                    time.sleep(self.sleep_interval)
                    continue

                # 2️⃣ detect regime (SAFE)
                regime = "UNKNOWN"
                if self.regime_memory:
                    regime = self.regime_memory.current_regime()

                # 3️⃣ mutate regime aware
                if self.mutation:
                    genome = self.mutation.mutate(
                        genome,
                        regime=regime
                    )

                # 4️⃣ multi symbol expansion
                symbols = ["NSE:NIFTY", "NSE:BANKNIFTY"]

                if self.multi_symbol_engine:
                    symbols = self.multi_symbol_engine.select_symbols()

                # 5️⃣ submit to grid
                if self.grid:

                    self.grid.submit_genome_sweep(
                        [genome],
                        symbols=symbols,
                        periods=300
                    )

                logger.info(
                    "[research_loop] genome submitted | res=%s regime=%s",
                    self.resolution,
                    regime
                )

            except Exception as e:
                logger.exception(
                    "[research_loop] organism crash recovered"
                )

            time.sleep(self.sleep_interval)