import time
import logging
import random

from quant_ecosystem.research.alpha_intelligence.strategy_discovery_engine import StrategyDiscoveryEngine
from quant_ecosystem.research.alpha_intelligence.strategy_mutation_engine import StrategyMutationEngine
from quant_ecosystem.research.alpha_intelligence.alpha_evolution_engine import AlphaEvolutionEngine
from quant_ecosystem.research.alpha_intelligence.promotion_probability_engine import PromotionProbabilityEngine
from quant_ecosystem.research.alpha_intelligence.multi_symbol_intelligence import MultiSymbolIntelligence
from quant_ecosystem.research.alpha_intelligence.regime_learning_memory import RegimeLearningMemory

from dataclasses import dataclass, field
from typing import List, Dict, Any
import time


@dataclass
class LoopConfig:
    promote_threshold: float = -0.50
    max_cycles: int = 10
    sleep_between_cycles: float = 1.0
    discovery_batch: int = 5
    mutation_batch: int = 5
    regime_awareness: bool = True
    multi_symbol_eval: bool = True


@dataclass
class CycleState:
    cycle_id: str
    started_ts: float = field(default_factory=time.time)
    genomes_generated: int = 0
    genomes_evaluated: int = 0
    promoted: int = 0
    phases_skipped: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

logger = logging.getLogger(__name__)


class AutonomousResearchLoop:

    def __init__(
        self,
        research_grid,
        genome_library=None,
        resolution="M15",
        config=None,
        **engines,
    ):
        """
        Institutional Autonomous Research Organism
        Fully backward & forward compatible constructor
        """

        self.grid = research_grid
        self.genome_library = genome_library
        self.resolution = resolution
        self.config = config

        # absorb ANY engine passed
        self.discovery_engine = engines.get("discovery_engine")
        self.mutation_engine = engines.get("mutation_engine")
        self.evolution_engine = engines.get("evolution_engine")
        self.regime_engine = engines.get("regime_engine")
        self.meta_research_ai = engines.get("meta_research_ai")

        self._extra_engines = engines

        self._running = False
        self._cycle = 0

    # -------------------------------------------------------------

    def run_cycle(self):

        self.cycle += 1

        regime = self.regime_engine.current_regime()

        logger.info(f"[research_loop] Cycle {self.cycle} regime={regime}")

        # =============================
        # Step 1 — fetch elite genomes
        # =============================

        elites = self.library.top_genomes(25)

        # =============================
        # Step 2 — evolve alpha
        # =============================

        new_genomes = self.evolution.evolve(elites)

        logger.info(f"[research_loop] evolving {len(new_genomes)} genomes")

        # =============================
        # Step 3 — symbol routing
        # =============================

        symbols = self.symbol_ai.select_symbols(regime)

        # =============================
        # Step 4 — parallel evaluation
        # =============================

        job_ids = self.grid.submit_genome_sweep(
            new_genomes,
            symbols=symbols,
            periods=800
        )

        self.grid._wait_for_jobs(job_ids, timeout_sec=300)

        # =============================
        # Step 5 — fetch results
        # =============================

        results = self.grid.top_results(50)

        promoted = 0

        for r in results:

            fitness = r.fitness
            sharpe = r.sharpe
            gid = r.result.get("genome_id")

            prob = self.promoter.compute_probability(
                fitness=fitness,
                sharpe=sharpe,
                regime_score=self.regime_memory.regime_score(regime)
            )

            if random.random() < prob:

                genome_data = r.payload.copy()
                genome_data["fitness_score"] = fitness
                genome_data["source"] = "alpha_loop"

                self.library.store_genome(gid, genome_data)

                self.regime_memory.record(regime, fitness)

                promoted += 1

        logger.info(
            f"[research_loop] promoted {promoted} genomes | best={results[0].fitness if results else 0:.3f}"
        )

    # -------------------------------------------------------------

    def run_forever(self, sleep_sec=30):

        while True:

            try:
                self.run_cycle()
            except Exception as e:
                logger.exception("AutonomousResearchLoop failure")

            time.sleep(sleep_sec)


    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """
        Start autonomous research daemon loop.
        """
        if self._running:
            return

        import threading

        self._running = True

        t = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"ResearchLoop-{self.resolution}"
        )
        t.start()

    def stop(self):
        self._running = False


    def _run_loop(self):
        """
        Main research daemon.
        """
        import time
        import logging

        logger = logging.getLogger(__name__)

        logger.info("[research_loop] daemon started | resolution=%s", self.resolution)

        while self._running:

            try:
                self._cycle += 1

                # VERY SAFE minimal cycle
                if self.discovery_engine:
                    genomes = self.discovery_engine.discover_genomes(
                        resolution=self.resolution,
                        n=4
                    )

                    if genomes:
                        self.grid.submit_genome_sweep(genomes)

            except Exception as e:
                logger.warning("[research_loop] cycle error: %s", e)

            time.sleep(5)        