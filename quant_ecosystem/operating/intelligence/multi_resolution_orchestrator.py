import logging
from typing import Dict

from quant_ecosystem.research.autonomous_research.autonomous_research_loop import (
    AutonomousResearchLoop
)

logger = logging.getLogger(__name__)


class MultiResolutionResearchOrchestrator:

    def __init__(
        self,
        router=None,
        registry=None,
        resolution_registry=None,
        research_grid=None,
        discovery_engine=None,
        mutation_engine=None,
        evolution_engine=None,
        meta_research_ai=None,
        **_
    ):
        # ⭐ factory compatibility layer
        self.router = router
        self.registry = registry or resolution_registry
        self.research_grid = research_grid

        self.discovery_engine = discovery_engine
        self.mutation_engine = mutation_engine
        self.evolution_engine = evolution_engine
        self.meta_research_ai = meta_research_ai

        self._loops: Dict[str, AutonomousResearchLoop] = {}

    # -----------------------------------------------------

    def boot_research_fabric(self):

        logger.info("[orchestrator] booting multi-resolution research fabric")

        for resolution in self.registry.list_active_resolutions():

            logger.info(
                f"[orchestrator] spawning research organism for resolution={resolution}"
            )

            loop = AutonomousResearchLoop()

            self._loops[resolution] = loop

    # -----------------------------------------------------

    def start(self):

        self.boot_research_fabric()

        for resolution, loop in self._loops.items():

            logger.info(
                f"[orchestrator] starting research organism resolution={resolution}"
            )

            if hasattr(loop, "start"):
                loop.start()
            else:
                logger.warning(
                    f"[orchestrator] loop {resolution} has no start()"
                )

    # -----------------------------------------------------

    def stop(self):

        for resolution, loop in self._loops.items():

            logger.info(
                f"[orchestrator] stopping research organism resolution={resolution}"
            )

            if hasattr(loop, "stop"):
                loop.stop()