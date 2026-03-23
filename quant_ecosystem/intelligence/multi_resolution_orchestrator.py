import logging
from typing import Dict

from quant_ecosystem.intelligence.fabric_state import FabricState
from quant_ecosystem.autonomous_research.autonomous_research_loop import (
    AutonomousResearchLoop,
)

logger = logging.getLogger(__name__)


class MultiResolutionResearchOrchestrator:
    """
    Institutional command center controlling all research organisms.
    """

    def __init__(self, router, resolution_registry):

        self.router = router
        self.registry = resolution_registry
        self.fabric_state = FabricState()

        self.engines: Dict[str, AutonomousResearchLoop] = {}

        self._running = False

    # -----------------------------------------
    # FABRIC BOOT
    # -----------------------------------------

    def boot_research_fabric(self):

        logger.info("[orchestrator] booting multi-resolution research fabric")

        if hasattr(self.registry, "horizons"):
            resolutions = self.registry.horizons()

        elif hasattr(self.registry, "get_horizons"):
            resolutions = self.registry.get_horizons()

        elif hasattr(self.registry, "resolutions"):
            resolutions = self.registry.resolutions

        elif hasattr(self.registry, "_horizons"):
            resolutions = self.registry._horizons

        else:
            logger.warning(
                "[orchestrator] registry horizons not found → fallback default"
            )
            resolutions = ["M5", "M15", "H1", "D1"]

        for resolution in resolutions:

            logger.info(
                f"[orchestrator] spawning research organism for resolution={resolution}"
            )

            loop = AutonomousResearchLoop(
                research_grid=self.research_grid,
                genome_library=self.genome_library,
                regime_engine=self.regime_engine,
            )

            self.engines[resolution] = loop

    # -----------------------------------------
    # LIFECYCLE CONTROL
    # -----------------------------------------

    def start(self):

        if self._running:
            return

        self.boot_research_fabric()

        for resolution, engine in self.engines.items():
            logger.info(
                f"[orchestrator] starting research organism resolution={resolution}"
            )
            engine.start()

        self._running = True

    def stop(self):

        if not self._running:
            return

        for resolution, engine in self.engines.items():
            logger.info(
                f"[orchestrator] stopping research organism resolution={resolution}"
            )
            engine.stop()

        self._running = False

    # -----------------------------------------
    # INSTITUTIONAL CONTROL SURFACE (future expansion)
    # -----------------------------------------

    def throttle_resolution(self, resolution: str):

        if resolution in self.engines:
            logger.info(
                f"[orchestrator] throttling research organism resolution={resolution}"
            )
            self.engines[resolution].stop()

    def resume_resolution(self, resolution: str):

        if resolution in self.engines:
            logger.info(
                f"[orchestrator] resuming research organism resolution={resolution}"
            )
            self.engines[resolution].start()