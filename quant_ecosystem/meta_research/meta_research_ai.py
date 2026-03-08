import logging
import time
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ResearchPriorities:
    focus_family: str = "momentum"
    mutation_rate: float = 0.15
    target_markets: tuple = ("NSE", "CRYPTO")
    confidence: float = 0.0


class MetaResearchAI:
    """
    Oversees research direction.

    Learns from:
    - GenomeLibrary
    - ResearchGrid results
    - Strategy performance
    """

    def __init__(
        self,
        genome_library=None,
        research_grid=None,
        performance_store=None,
        regime_engine=None,
        refresh_interval_sec: int = 60,
        min_samples_for_confidence: int = 10,
    ):

        self.genome_library = genome_library
        self.research_grid = research_grid
        self.performance_store = performance_store
        self.regime_engine = regime_engine

        self.refresh_interval = refresh_interval_sec
        self.min_samples = min_samples_for_confidence

        self.priorities = ResearchPriorities()

        self._lock = threading.Lock()
        self._last_update = 0

        logger.info(
            "MetaResearchAI initialized | interval=%ss min_samples=%s lib=%s grid=%s perf=%s regime=%s",
            refresh_interval_sec,
            min_samples_for_confidence,
            "yes" if genome_library else "no",
            "yes" if research_grid else "no",
            "yes" if performance_store else "no",
            "yes" if regime_engine else "no",
        )

    def status(self) -> Dict[str, Any]:

        return {
            "focus_family": self.priorities.focus_family,
            "mutation_rate": self.priorities.mutation_rate,
            "target_markets": self.priorities.target_markets,
            "confidence": self.priorities.confidence,
        }

    def force_refresh(self):

        with self._lock:

            logger.info("MetaResearchAI refreshing research priorities")

            try:
                if self.genome_library:

                    stats = self.genome_library.get_stats()

                    if stats.get("best_family"):

                        self.priorities.focus_family = stats["best_family"]

                if self.research_grid:

                    grid_stats = self.research_grid.get_stats()

                    if grid_stats.get("avg_fitness"):

                        fitness = grid_stats["avg_fitness"]

                        if fitness > 1.0:
                            self.priorities.mutation_rate = 0.10
                        elif fitness < 0:
                            self.priorities.mutation_rate = 0.25

                self.priorities.confidence = min(
                    1.0,
                    self.priorities.confidence + 0.05
                )

                self._last_update = time.time()

                logger.info(
                    "MetaResearchAI updated | focus=%s mutation=%.2f confidence=%.2f",
                    self.priorities.focus_family,
                    self.priorities.mutation_rate,
                    self.priorities.confidence,
                )

            except Exception as e:

                logger.warning("MetaResearchAI refresh failed: %s", e)

    def get_priorities(self) -> ResearchPriorities:

        with self._lock:
            return self.priorities