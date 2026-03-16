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

        if not self.registry:
            logger.warning(
                "[orchestrator] ResolutionRegistry missing — research fabric not started"
            )
            return

        for resolution in self.registry.list_active_resolutions():

            logger.info(
                f"[orchestrator] spawning research organism for resolution={resolution}"
            )

            loop = AutonomousResearchLoop(
                discovery_engine = getattr(self.router, "strategy_discovery_engine", None),
                mutation_engine  = getattr(self.router, "strategy_mutation_engine", None),
                evolution_engine = getattr(self.router, "alpha_evolution_engine", None),
                research_grid    = getattr(self.router, "research_grid", None),
                genome_library   = getattr(self.router, "genome_library", None),
                meta_research_ai = getattr(self.router, "meta_research_ai", None),
                strategy_bank_engine = getattr(self.router, "strategy_bank_engine", None),
                strategy_registry    = getattr(self.router, "strategy_registry", None),
                resolution = resolution,
                registry   = self.registry,
                fabric_state = self.fabric_state,
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