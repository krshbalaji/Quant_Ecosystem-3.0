"""
Quant Ecosystem 3.0 — System Factory & Router
==============================================
Dependency-injection factory that assembles all subsystems into a single
SystemRouter object.  Imports are deferred inside factory methods so no
module touches external services at import time and circular-import
chains are broken at the architectural level.

Operating Modes
---------------
RESEARCH  — Market data + research stack only (no broker, no execution).
PAPER     — Research stack + paper execution engine (simulated orders).
LIVE      — Full stack including real broker connection.

Boot order within each mode is deterministic: each subsystem is listed
explicitly in its construction call, making the dependency graph visible
at a glance and easy to audit.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Operating Mode
# ─────────────────────────────────────────────────────────────────────────────

class OperatingMode(str, Enum):
    """Canonical set of system operating modes."""
    RESEARCH = "RESEARCH"
    PAPER    = "PAPER"
    LIVE     = "LIVE"

    @classmethod
    def from_str(cls, value: str) -> "OperatingMode":
        normalized = str(value).strip().upper()
        try:
            return cls(normalized)
        except ValueError:
            logger.warning(
                "Unknown operating mode '%s' — defaulting to PAPER.", value
            )
            return cls.PAPER


# ─────────────────────────────────────────────────────────────────────────────
# System Router
# ─────────────────────────────────────────────────────────────────────────────

class SystemRouter:
    """
    Top-level runtime container that MasterOrchestrator receives.

    Holds references to every subsystem as optional attributes.  Any
    attribute not wired for the current mode is ``None``.  The
    MasterOrchestrator probes attributes via ``getattr(router, key, None)``
    so missing modules are silently skipped.

    MasterOrchestrator compatibility
    ---------------------------------
    * ``router.system``           → self   (orchestrator reads engine attrs)
    * ``router.execute(...)``     → async delegate to ExecutionRouter
    * ``router.stop_trading()``   → state delegate
    * ``router.set_auto_mode()``  → state delegate
    * All engine attrs accessed via getattr(router, "...", None)
    """

    def __init__(self, config: Any) -> None:
        self.config: Any = config

        # ── Core ──────────────────────────────────────────────────────────────
        self.state:            Optional[Any] = None
        self.market_data:      Optional[Any] = None
        self.symbols:          list          = []

        # ── Execution ─────────────────────────────────────────────────────────
        self._execution_router: Optional[Any] = None   # internal ExecutionRouter
        self.risk_engine:       Optional[Any] = None
        self.portfolio_engine:  Optional[Any] = None
        self.execution_lock:    Optional[Any] = None   # set by orchestrator

        # ── Broker ────────────────────────────────────────────────────────────
        self._broker:         Optional[Any] = None
        self._broker_router:  Optional[Any] = None
        self.reconciler:      Optional[Any] = None
        self.capital_governance: Optional[Any] = None
        self.position_sizer:  Optional[Any] = None

        # ── Strategy layer ────────────────────────────────────────────────────
        self.strategy_engine:          Optional[Any] = None
        self.strategy_registry:        Optional[Any] = None
        self.strategy_bank_engine:     Optional[Any] = None
        self.strategy_bank_layer:      Optional[Any] = None
        self.strategy_selector:        Optional[Any] = None
        self.capital_allocator_engine: Optional[Any] = None
        self.meta_strategy_brain:      Optional[Any] = None
        self.strategy_diversity_engine: Optional[Any] = None
        self.strategy_survival_engine: Optional[Any] = None
        self.mutation_engine:          Optional[Any] = None

        # ── Research & Alpha ──────────────────────────────────────────────────
        self.alpha_scanner:           Optional[Any] = None
        self.strategy_lab_controller: Optional[Any] = None
        self.alpha_genome_library:    Optional[Any] = None
        self.alpha_genome_generator:  Optional[Any] = None
        self.alpha_genome_evaluator:  Optional[Any] = None
        self.alpha_factory_controller: Optional[Any] = None
        self.strategy_discovery:      Optional[Any] = None
        self.alpha_competition:       Optional[Any] = None
        self.alpha_evolution:         Optional[Any] = None
        self.capital_intelligence:    Optional[Any] = None

        # ── AI / ML ───────────────────────────────────────────────────────────
        self.portfolio_ai_engine:     Optional[Any] = None
        self.adaptive_learning_engine: Optional[Any] = None
        self.cognitive_controller:    Optional[Any] = None
        self.regime_ai_engine:        Optional[Any] = None
        self.market_regime_detector:  Optional[Any] = None

        # ── Market intelligence ───────────────────────────────────────────────
        self.global_market_brain:     Optional[Any] = None
        self.market_pulse_engine:     Optional[Any] = None
        self.event_signal_engine:     Optional[Any] = None
        self.event_driven_orchestrator: Optional[Any] = None
        self.event_bus:               Optional[Any] = None
        self.autonomous_controller:   Optional[Any] = None

        # ── Risk & Safety ─────────────────────────────────────────────────────
        self.safety_governor:         Optional[Any] = None

        # ── Shadow / paper ────────────────────────────────────────────────────
        self.shadow_trading_engine:   Optional[Any] = None
        self.outcome_memory:          Optional[Any] = None

        # ── Communication ─────────────────────────────────────────────────────
        self.telegram:                Optional[Any] = None

        # ── Dashboard configs ─────────────────────────────────────────────────
        self.dashboard_service_config: Optional[dict] = None
        self.cockpit_service_config:   Optional[dict] = None

        # ── Parallel research grid  (CPU-parallel evaluation)  ← NEW ─────────
        self.research_grid:            Optional[Any] = None

        # ── Backtest engine (injectable into ResearchGrid)  ← NEW ────────────
        self.backtest_engine:          Optional[Any] = None

        # ── genome_library: canonical DI name (same object as alpha_genome_library)
        self.genome_library:           Optional[Any] = None

        # ── Data router (synthetic / CSV / broker OHLCV adapters)  ← NEW ─────
        self.data_router:              Optional[Any] = None

        # ── Meta-Research AI (guides discovery via memory analysis) ← NEW ────
        self.meta_research_ai:         Optional[Any] = None

    # ── MasterOrchestrator compatibility ──────────────────────────────────────

    @property
    def system(self) -> "SystemRouter":
        """Allow MasterOrchestrator to access engines via router.system.*"""
        return self

    @property
    def execution_router(self) -> Optional[Any]:
        """Expose internal ExecutionRouter for legacy compatibility checks."""
        return self._execution_router

    # ── ExecutionRouter delegation ────────────────────────────────────────────

    async def execute(self, signal: Any = None, market_bias: str = "NEUTRAL",
                      regime: str = "MEAN_REVERSION") -> dict:
        """Async execution entry point — delegates to ExecutionRouter."""
        if self._execution_router is None:
            return {"status": "SKIP", "reason": "EXECUTION_ROUTER_NOT_INITIALIZED"}
        return await self._execution_router.execute(
            signal=signal, market_bias=market_bias, regime=regime
        )

    def stop_trading(self) -> None:
        if self.state is not None:
            self.state.trading_halted = True
            logger.warning("Trading halted via SystemRouter.stop_trading().")

    def set_auto_mode(self, enabled: bool) -> None:
        if self.state is not None:
            self.state.auto_mode = bool(enabled)
            logger.info("Auto mode set to %s.", enabled)

    # Expose _build_snapshots if ExecutionRouter implements it
    def _build_snapshots(self, **kwargs: Any) -> list:
        if self._execution_router is not None and hasattr(
            self._execution_router, "_build_snapshots"
        ):
            return self._execution_router._build_snapshots(**kwargs)
        return []

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _attach_execution_router(self, er: Any) -> None:
        """
        Wire the ExecutionRouter into this SystemRouter.
        Copies references the orchestrator expects directly on router.
        """
        self._execution_router = er
        # Expose broker attribute from ExecutionRouter if present
        if hasattr(er, "broker"):
            self._broker_router = er.broker

    def _log_mode_summary(self, mode: OperatingMode) -> None:
        active_engines = [
            name for name in (
                "market_data", "state", "risk_engine",
                "strategy_engine", "strategy_bank_engine",
                "alpha_scanner", "portfolio_ai_engine",
                "shadow_trading_engine", "telegram",
                "global_market_brain", "safety_governor",
                "research_grid", "meta_research_ai",
            )
            if getattr(self, name, None) is not None
        ]
        logger.info(
            "SystemRouter wired | mode=%s | active_engines=%s",
            mode.value, active_engines,
        )


# ─────────────────────────────────────────────────────────────────────────────
# System Factory
# ─────────────────────────────────────────────────────────────────────────────

class SystemFactory:
    """
    Dependency-injection factory.

    Construction pattern
    --------------------
    All subsystem classes are imported inside factory methods, never at
    module level.  This eliminates circular imports caused by inter-module
    class references at load time and ensures no external service is
    contacted during ``import``.

    Dependency order is explicit: every constructor argument names the
    exact object being injected, making the dependency graph self-documenting.
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._mode = OperatingMode.from_str(
            str(getattr(config, "mode", "PAPER"))
        )

    # ── Public entry point ────────────────────────────────────────────────────

    def build(self) -> SystemRouter:
        """
        Assemble and return a fully wired SystemRouter.

        Boot order:
            1. Core layer      (state, market data, risk)
            2. Research layer  (always, alpha is the foundation)
            3. Execution layer (PAPER / LIVE only)
            4. Strategy layer  (PAPER / LIVE only)
            5. Intelligence    (optional, config-gated)
            6. Safety          (optional, config-gated)
            7. Communication   (optional, config-gated)
            8. Dashboard       (optional, config-gated)
        """
        logger.info("SystemFactory.build() | mode=%s", self._mode.value)

        router = SystemRouter(config=self._config)

        self._boot_core_layer(router)           # 1. core

        if self._mode in (OperatingMode.PAPER, OperatingMode.LIVE):
            self._boot_execution_layer(router)   # 2. execution
            self._boot_strategy_layer(router)    # 3. strategy

        if self._mode is OperatingMode.LIVE:
            self._boot_live_broker(router)       # 4. live broker

        self._boot_intelligence_layer(router)    # 5. intelligence
        self._boot_safety_layer(router)          # 6. safety
        self._boot_communication_layer(router)   # 7. communication
        self._boot_research_memory(router)       # 8. research_memory
        self._boot_genome_memory(router)         # 9. genome_memory
        self._boot_synthetic_market(router)      # 10. synthetic_market
        self._boot_autonomous_lab(router)        # 11. autonomous_lab
        self._boot_research_grid(router)         # 12. research_grid ← NEW
        self._boot_meta_research(router)         # 13. meta_research  ← NEW
        self._boot_dashboard_layer(router)       # 14. dashboard

        router._log_mode_summary(self._mode)
        return router

    # ── Layer builders ────────────────────────────────────────────────────────

    def _boot_core_layer(self, router: SystemRouter) -> None:
        """State, market universe, market data engine, risk engine."""
        logger.info("[boot] core layer …")

        # System state
        try:
            from quant_ecosystem.core.system_state import SystemState  # noqa: PLC0415
            router.state = SystemState()
            router.state.trading_mode = self._mode.value
            logger.debug("SystemState initialized.")
        except Exception:
            logger.exception("Failed to initialize SystemState.")
            raise

        # Market universe
        universe = None
        try:
            from quant_ecosystem.market.market_universe_manager import (  # noqa: PLC0415
                MarketUniverseManager,
            )
            universe = MarketUniverseManager(self._config)
            logger.debug("MarketUniverseManager initialized.")
        except Exception:
            logger.warning("MarketUniverseManager unavailable.", exc_info=True)

        # Market data engine
        try:
            from quant_ecosystem.market.market_data_engine import (  # noqa: PLC0415
                MarketDataEngine,
            )
            router.market_data = MarketDataEngine(self._config, universe)
            logger.debug("MarketDataEngine initialized.")
        except Exception:
            logger.warning("MarketDataEngine unavailable.", exc_info=True)

        # Risk engine
        try:
            from quant_ecosystem.risk.risk_engine import RiskEngine  # noqa: PLC0415
            router.risk_engine = RiskEngine(config=self._config)
            logger.debug("RiskEngine initialized.")
        except Exception:
            logger.warning("RiskEngine unavailable.", exc_info=True)

        # Portfolio engine
        try:
            from quant_ecosystem.portfolio.portfolio_engine import (  # noqa: PLC0415
                PortfolioEngine,
            )
            router.portfolio_engine = PortfolioEngine()
            logger.debug("PortfolioEngine initialized.")
        except Exception:
            logger.warning("PortfolioEngine unavailable.", exc_info=True)

        # Outcome memory (persistent trade context)
        try:
            from quant_ecosystem.core.persistence.outcome_memory import (  # noqa: PLC0415
                OutcomeMemory,
            )
            router.outcome_memory = OutcomeMemory()
            logger.debug("OutcomeMemory initialized.")
        except Exception:
            logger.debug("OutcomeMemory unavailable (non-critical).")

    def _boot_research_memory(self, router: SystemRouter) -> None:
        """
        Research dataset builders, strategy discovery, mutation,
        evolution, capital intelligence, and backtest engine.
        """
        logger.info("[boot] research_memory …")
        cfg = self._config

        # Core backtest engine — exposed for DI into ResearchGrid
        try:
            from quant_ecosystem.research.backtest.backtest_engine import (  # noqa: PLC0415
                BacktestEngine,
            )
            router.backtest_engine = BacktestEngine()
            logger.debug("BacktestEngine initialized.")
        except Exception:
            logger.warning("BacktestEngine unavailable.", exc_info=True)

        # Research dataset builder
        dataset_builder = None
        try:
            from quant_ecosystem.research.research_dataset_builder import (  # noqa: PLC0415
                ResearchDatasetBuilder,
            )
            dataset_builder = ResearchDatasetBuilder(router.market_data)
            logger.debug("ResearchDatasetBuilder initialized.")
        except Exception:
            logger.warning("ResearchDatasetBuilder unavailable.", exc_info=True)

        # Factor dataset builder (Factor Library Engine)
        factor_builder = None
        try:
            from quant_ecosystem.research.factor_dataset_builder import (  # noqa: PLC0415
                FactorDatasetBuilder,
            )
            factor_builder = FactorDatasetBuilder(dataset_builder)
            logger.debug("FactorDatasetBuilder initialized.")
        except Exception:
            logger.warning("FactorDatasetBuilder unavailable.", exc_info=True)

        # Distributed research engine (grid worker pool)
        distributed_engine = None
        try:
            from quant_ecosystem.research.distributed_research_engine import (  # noqa: PLC0415
                DistributedResearchEngine,
            )
            distributed_engine = DistributedResearchEngine()
            logger.debug("DistributedResearchEngine initialized.")
        except Exception:
            logger.warning("DistributedResearchEngine unavailable.", exc_info=True)

        # Strategy discovery engine (Alpha Strategy Generator)
        try:
            from quant_ecosystem.research.strategy_discovery_engine import (  # noqa: PLC0415
                StrategyDiscoveryEngine,
            )
            router.strategy_discovery = StrategyDiscoveryEngine(
                dataset_builder=dataset_builder,
                factor_builder=factor_builder,
                distributed_engine=distributed_engine,
                research_grid=None,   # injected in _boot_research_grid
            )
            logger.debug("StrategyDiscoveryEngine initialized.")
        except Exception:
            logger.warning("StrategyDiscoveryEngine unavailable.", exc_info=True)

        # Strategy mutation engine (Strategy Mutation Engine)
        try:
            from quant_ecosystem.research.strategy_mutation_engine import (  # noqa: PLC0415
                StrategyMutationEngine,
            )
            router.mutation_engine = StrategyMutationEngine()
            logger.debug("StrategyMutationEngine initialized.")
        except Exception:
            logger.warning("StrategyMutationEngine unavailable.", exc_info=True)

        # Alpha evolution engine (Alpha Genome Engine)
        try:
            from quant_ecosystem.evolution.alpha_evolution_engine import (  # noqa: PLC0415
                AlphaEvolutionEngine,
            )
            router.alpha_evolution = AlphaEvolutionEngine(
                router.strategy_discovery,
                router.mutation_engine,
            )
            logger.debug("AlphaEvolutionEngine initialized.")
        except Exception:
            logger.warning("AlphaEvolutionEngine unavailable.", exc_info=True)

        # Capital Intelligence Engine
        try:
            from quant_ecosystem.portfolio.capital_intelligence_engine import (  # noqa: PLC0415
                CapitalIntelligenceEngine,
            )
            router.capital_intelligence = CapitalIntelligenceEngine(cfg)
            logger.debug("CapitalIntelligenceEngine initialized.")
        except Exception:
            logger.warning("CapitalIntelligenceEngine unavailable.", exc_info=True)

        # (genome_memory and autonomous_lab are booted separately in build())

    def _boot_genome_memory(self, router: SystemRouter) -> None:
        """
        Genome library (always), plus generator/evaluator/factory
        when enable_alpha_genome_engine is set.

        router.genome_library is the canonical DI target for ResearchGrid.
        """
        logger.info("[boot] genome_memory …")
        cfg = self._config  # noqa: F841

        # Always boot genome library — ResearchGrid depends on it
        try:
            from quant_ecosystem.genome_library.genome_library import (  # noqa: PLC0415
                GenomeLibrary,
            )
            lib = GenomeLibrary()
            router.genome_library       = lib
            router.alpha_genome_library = lib
            logger.debug("GenomeLibrary initialized.")
        except Exception:
            logger.debug("GenomeLibrary unavailable — trying AlphaGenomeLibrary.")
            try:
                from quant_ecosystem.alpha_genome.genome_library import (  # noqa: PLC0415
                    AlphaGenomeLibrary,
                )
                lib = AlphaGenomeLibrary()
                router.genome_library       = lib
                router.alpha_genome_library = lib
                logger.debug("AlphaGenomeLibrary (fallback) initialized.")
            except Exception:
                logger.debug("AlphaGenomeLibrary unavailable (non-critical).")

        if not getattr(cfg, "enable_alpha_genome_engine", False):
            return
        try:
            from quant_ecosystem.alpha_genome.genome_generator import (  # noqa: PLC0415
                GenomeGenerator,
            )
            router.alpha_genome_generator = GenomeGenerator()
            logger.debug("GenomeGenerator initialized.")
        except Exception:
            logger.warning("GenomeGenerator unavailable.", exc_info=True)

        try:
            from quant_ecosystem.alpha_genome.genome_generator import (  # noqa: PLC0415
                GenomeGenerator,
            )
            router.alpha_genome_generator = GenomeGenerator()
            logger.debug("GenomeGenerator initialized.")
        except Exception:
            logger.warning("GenomeGenerator unavailable.", exc_info=True)

        try:
            from quant_ecosystem.alpha_genome.genome_evaluator import (  # noqa: PLC0415
                GenomeEvaluator,
            )
            router.alpha_genome_evaluator = GenomeEvaluator()
            logger.debug("GenomeEvaluator initialized.")
        except Exception:
            logger.warning("GenomeEvaluator unavailable.", exc_info=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Boot step 10 — Synthetic market
    # ─────────────────────────────────────────────────────────────────────────

    def _boot_synthetic_market(self, router: SystemRouter) -> None:
        """
        DataRouter — multi-source OHLCV data with a guaranteed synthetic
        fallback so the research grid can always generate price series even
        when live broker credentials are absent.
        """
        logger.info("[boot] synthetic_market …")
        cfg = self._config

        try:
            from quant_ecosystem.data.data_router import DataRouter  # noqa: PLC0415
            router.data_router = DataRouter(
                mode=self._mode.value,
                fyers_broker=router._broker,
                csv_dir=str(getattr(cfg, "csv_data_dir", "") or ""),
            )
            logger.debug("DataRouter initialized.")
        except Exception:
            logger.debug("DataRouter unavailable (synthetic fallback active).")

    # ─────────────────────────────────────────────────────────────────────────
    # Boot step 12 — Research grid  ← NEW
    # ─────────────────────────────────────────────────────────────────────────

    def _boot_research_grid(self, router: SystemRouter) -> None:
        """
        Parallel CPU research grid.

        Wires ``router.genome_library`` and ``router.backtest_engine`` into
        ResearchGrid, then injects the live grid into StrategyDiscoveryEngine
        so that all genome evaluations are dispatched in parallel across all
        CPU cores.

        Safety guarantee
        ----------------
        Any failure here leaves ``router.research_grid = None`` and the
        system continues normally with single-threaded evaluation inside
        ``StrategyDiscoveryEngine``.  No exception propagates to the caller.
        """
        logger.info("[boot] research_grid …")
        cfg = self._config

        if not getattr(cfg, "enable_research_grid", True):
            logger.info(
                "ResearchGrid disabled via config — single-threaded evaluation active."
            )
            return

        try:
            from quant_ecosystem.research.grid import ResearchGrid  # noqa: PLC0415

            n_workers         = max(1, int(getattr(cfg, "research_grid_workers", 0)))
            promote_threshold = float(
                getattr(cfg, "research_grid_promote_threshold", 0.5)
            )
            
            grid = ResearchGrid(
                n_workers=n_workers,
                promote_threshold=promote_threshold,
                genome_library=router.genome_library,    # injected — may be None
                backtest_engine=router.backtest_engine,  # injected — may be None
                result_callback=_make_grid_result_callback(router),
            )

            # Start the worker pool — fall back gracefully on failure
            try:
                grid.start()
                logger.info(
                    "ResearchGrid started | workers=%d pool=%s threshold=%.2f",
                    grid._n_workers,
                    grid._pool.pool_type,
                    promote_threshold,
                )
            except Exception as start_exc:
                logger.warning(
                    "ResearchGrid.start() failed (%s) — "
                    "falling back to single-threaded evaluation.",
                    start_exc,
                )
                grid = None

            router.research_grid = grid

            # Late-inject into StrategyDiscoveryEngine (created in step 8)
            if grid is not None and router.strategy_discovery is not None:
                if hasattr(router.strategy_discovery, "set_research_grid"):
                    router.strategy_discovery.set_research_grid(grid)
                    logger.debug(
                        "ResearchGrid injected into StrategyDiscoveryEngine."
                    )

        except Exception as exc:
            logger.warning(
                "ResearchGrid boot failed (%s) — "
                "system continues with single-threaded evaluation.",
                exc,
            )
            router.research_grid = None
            if router.strategy_discovery and router.research_grid:
                router.strategy_discovery.set_research_grid(router.research_grid)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Boot step 13 — Meta-Research AI  ← NEW
    # ─────────────────────────────────────────────────────────────────────────

    def _boot_meta_research(self, router: SystemRouter) -> None:
        """
        Meta-Research AI layer (boot step 13).

        Wires GenomeLibrary, ResearchGrid, PerformanceStore and RegimeEngine
        into MetaResearchAI, then late-injects the live instance into
        StrategyDiscoveryEngine so every discover() cycle is guided by
        data-driven research priorities.

        Safety guarantee
        ----------------
        Any failure here leaves ``router.meta_research_ai = None`` and
        StrategyDiscoveryEngine continues with its built-in defaults.
        No exception propagates to the caller.
        """
        logger.info("[boot] meta_research …")
        cfg = self._config

        if not getattr(cfg, "enable_meta_research", True):
            logger.info(
                "MetaResearchAI disabled via config — discovery uses built-in defaults."
            )
            return

        try:
            from quant_ecosystem.meta_research import MetaResearchAI  # noqa: PLC0415

            refresh_interval = float(
                getattr(cfg, "meta_research_refresh_interval_sec", 60.0)
            )
            min_samples = int(
                getattr(cfg, "meta_research_min_samples", 10)
            )

            # Resolve PerformanceStore — live in the research module
            perf_store = None
            try:
                from quant_ecosystem.research.performance_store import (  # noqa: PLC0415
                    PerformanceStore,
                )
                perf_store = PerformanceStore()
                logger.debug("MetaResearchAI: PerformanceStore created.")
            except Exception as exc:
                logger.debug("MetaResearchAI: PerformanceStore unavailable (%s).", exc)

            meta_ai = MetaResearchAI(
                genome_library          = router.genome_library,
                research_grid           = router.research_grid,
                performance_store       = perf_store,
                regime_engine           = (
                    router.regime_ai_engine
                    or router.market_regime_detector
                ),
                refresh_interval_sec    = refresh_interval,
                min_samples_for_confidence = min_samples,
            )

            router.meta_research_ai = meta_ai

            # Late-inject into StrategyDiscoveryEngine
            if router.strategy_discovery is not None:
                if hasattr(router.strategy_discovery, "set_meta_research_ai"):
                    router.strategy_discovery.set_meta_research_ai(meta_ai)
                    logger.debug(
                        "MetaResearchAI injected into StrategyDiscoveryEngine."
                    )

            # Warm up: run first analysis immediately (non-blocking)
            try:
                initial = meta_ai.prioritise()
                logger.info(
                    "MetaResearchAI ready | focus=%s mutation=%.2f markets=%s confidence=%.2f",
                    initial.focus_family,
                    initial.mutation_rate,
                    initial.explore_markets,
                    initial.confidence,
                )
            except Exception as exc:
                logger.debug("MetaResearchAI warmup failed (%s) — will retry on first call.", exc)

        except Exception as exc:
            logger.warning(
                "MetaResearchAI boot failed (%s) — discovery uses built-in defaults.",
                exc,
            )
            router.meta_research_ai = None

    # ─────────────────────────────────────────────────────────────────────────
    # Alpha factory helper (used by _boot_genome_memory)
    # ─────────────────────────────────────────────────────────────────────────

    def _boot_alpha_factory(self, router: SystemRouter) -> None:
        """Alpha Factory — idea generator, candidate filter, promotion pipeline."""
        try:
            from quant_ecosystem.alpha_factory.factory_controller import (  # noqa: PLC0415
                FactoryController,
            )
            router.alpha_factory_controller = FactoryController(
                config=self._config,
                genome_library=router.alpha_genome_library,
            )
            logger.debug("FactoryController (AlphaFactory) initialized.")
        except Exception:
            logger.warning("AlphaFactory unavailable.", exc_info=True)

    def _boot_autonomous_lab(self, router: SystemRouter) -> None:
        """Strategy Lab backtest sandbox (autonomous_lab boot step)."""
        logger.info("[boot] autonomous_lab …")
        cfg = self._config

        if not getattr(cfg, "enable_strategy_lab", False):
            logger.debug("StrategyLab disabled via config.")
            return

        try:
            from quant_ecosystem.strategy_lab.lab_controller import (  # noqa: PLC0415
                StrategyLabController,
            )
            router.strategy_lab_controller = StrategyLabController(
                strategy_bank_layer=router.strategy_bank_layer,
                backtest_engine=router.backtest_engine,
            )
            logger.debug("StrategyLabController initialized.")
        except Exception:
            logger.warning("StrategyLab unavailable.", exc_info=True)

    def _boot_execution_layer(self, router: SystemRouter) -> None:
        """
        Execution Router wired to a paper (simulated) broker by default.
        LIVE mode overlays the real broker in _boot_live_broker().
        """
        logger.info("[boot] execution layer (PAPER) …")

        # Paper broker — always available without API credentials
        try:
            from quant_ecosystem.broker.fyers_broker import FyersBroker  # noqa: PLC0415
            broker = FyersBroker(config=self._config)
            router._broker = broker
            logger.debug("FyersBroker (paper/simulated) initialized.")
        except Exception:
            logger.warning("FyersBroker unavailable — using no-op broker.", exc_info=True)
            broker = _NoOpBroker()
            router._broker = broker

        # Broker router (thin wrapper)
        try:
            from quant_ecosystem.broker.broker_router import BrokerRouter  # noqa: PLC0415
            broker_router = BrokerRouter(broker=broker)
            router._broker_router = broker_router
            logger.debug("BrokerRouter initialized.")
        except Exception:
            logger.warning("BrokerRouter unavailable.", exc_info=True)
            broker_router = broker  # fallback: use broker directly

        # Reconciler (optional, non-fatal)
        reconciler = None
        try:
            from quant_ecosystem.broker.reconciliation.broker_reconciler import (  # noqa: PLC0415
                BrokerReconciler,
            )
            reconciler = BrokerReconciler(
                broker=broker_router,
                state=router.state,
                portfolio=router.portfolio_engine,
            )
            router.reconciler = reconciler
            logger.debug("BrokerReconciler initialized.")
        except Exception:
            logger.debug("BrokerReconciler unavailable (non-critical).")

        # ExecutionRouter — main execution engine
        try:
            from quant_ecosystem.execution.execution_router import (  # noqa: PLC0415
                ExecutionRouter,
            )
            er = ExecutionRouter(
                broker=broker_router,
                risk_engine=router.risk_engine,
                state=router.state,
                market_data=router.market_data,
                portfolio_engine=router.portfolio_engine,
                reconciler=reconciler,
                symbols=router.symbols or list(getattr(self._config, "trade_symbols", [])),
                outcome_memory=router.outcome_memory,
            )
            router._attach_execution_router(er)
            logger.debug("ExecutionRouter initialized.")
        except Exception:
            logger.exception("ExecutionRouter initialization failed — execution unavailable.")

    def _boot_live_broker(self, router: SystemRouter) -> None:
        """
        LIVE mode: attempt to connect the real broker and swap it in.
        If connection fails, log a critical error and abort — do not fall
        back to paper silently in LIVE mode.
        """
        logger.info("[boot] live broker connection …")
        broker_name = str(getattr(self._config, "broker_name", "FYERS") or "FYERS").upper()

        try:
            if broker_name == "FYERS":
                from quant_ecosystem.broker.fyers_broker import FyersBroker  # noqa: PLC0415
                live_broker = FyersBroker(config=self._config)
            elif broker_name == "COINSWITCH":
                from quant_ecosystem.broker.coinswitch_broker import (  # noqa: PLC0415
                    CoinSwitchBroker,
                )
                live_broker = CoinSwitchBroker()
            else:
                raise ValueError(f"Unsupported broker: {broker_name!r}")

            from quant_ecosystem.broker.broker_router import BrokerRouter  # noqa: PLC0415
            live_broker_router = BrokerRouter(broker=live_broker)

            # Rewire ExecutionRouter to the live broker
            if router._execution_router is not None:
                router._execution_router.broker = live_broker_router
                router._broker = live_broker
                router._broker_router = live_broker_router

            logger.info("Live broker '%s' connected successfully.", broker_name)

        except Exception:
            logger.critical(
                "LIVE broker connection failed for '%s'. "
                "Refusing to continue — set MODE=PAPER for simulated trading.",
                broker_name,
                exc_info=True,
            )
            raise

    def _boot_strategy_layer(self, router: SystemRouter) -> None:
        """
        Strategy registry, live strategy engine, strategy bank,
        selector, capital allocator, meta alpha engine.
        """
        logger.info("[boot] strategy layer …")
        cfg = self._config

        # Strategy registry
        try:
            from quant_ecosystem.core.strategy_registry import (  # noqa: PLC0415
                StrategyRegistry,
            )
            router.strategy_registry = StrategyRegistry()
            logger.debug("StrategyRegistry initialized.")
        except Exception:
            logger.warning("StrategyRegistry unavailable.", exc_info=True)

        # Live strategy engine
        try:
            from quant_ecosystem.strategy_bank.live_strategy_engine import (  # noqa: PLC0415
                LiveStrategyEngine,
            )
            router.strategy_engine = LiveStrategyEngine(
                strategy_registry=router.strategy_registry
            )
            # Propagate to ExecutionRouter
            if router._execution_router is not None:
                router._execution_router.strategy_engine = router.strategy_engine
            logger.debug("LiveStrategyEngine initialized.")
        except Exception:
            logger.warning("LiveStrategyEngine unavailable.", exc_info=True)

        # Strategy bank (enabled via config flag)
        if getattr(cfg, "enable_strategy_bank", True):
            self._boot_strategy_bank(router)

        # Meta strategy brain (ensemble + regime routing)
        if getattr(cfg, "enable_meta_strategy_brain", False):
            self._boot_meta_strategy_brain(router)

        # Strategy diversity engine
        if getattr(cfg, "enable_strategy_diversity", False):
            self._boot_strategy_diversity(router)

        # Strategy survival engine
        if getattr(cfg, "enable_strategy_survival", False):
            self._boot_strategy_survival(router)

        # Alpha scanner
        if getattr(cfg, "enable_alpha_scanner", False):
            self._boot_alpha_scanner(router)

        # Portfolio AI
        if getattr(cfg, "enable_portfolio_ai", False):
            self._boot_portfolio_ai(router)

        # Shadow trading
        if getattr(cfg, "enable_shadow_trading", False):
            self._boot_shadow_trading(router)

    def _boot_strategy_bank(self, router: SystemRouter) -> None:
        """Strategy Bank Engine + bank layer."""
        try:
            from quant_ecosystem.strategy_bank.engine.strategy_bank_engine import (  # noqa: PLC0415
                StrategyBankEngine,
            )
            router.strategy_bank_engine = StrategyBankEngine(config=self._config)
            logger.debug("StrategyBankEngine initialized.")
        except Exception:
            logger.warning("StrategyBankEngine unavailable.", exc_info=True)

        try:
            from quant_ecosystem.strategy_bank.layer import (  # noqa: PLC0415
                StrategyBankLayer,
            )
            router.strategy_bank_layer = StrategyBankLayer(
                config=self._config,
                engine=router.strategy_bank_engine,
            )
            logger.debug("StrategyBankLayer initialized.")
        except Exception:
            logger.warning("StrategyBankLayer unavailable.", exc_info=True)

        try:
            from quant_ecosystem.strategy_selector.selector_core import (  # noqa: PLC0415
                SelectorCore,
            )
            router.strategy_selector = SelectorCore(
                config=self._config,
                bank_layer=router.strategy_bank_layer,
            )
            logger.debug("SelectorCore initialized.")
        except Exception:
            logger.warning("StrategySelectorCore unavailable.", exc_info=True)

        try:
            from quant_ecosystem.capital_allocator.allocation_engine import (  # noqa: PLC0415
                AllocationEngine,
            )
            router.capital_allocator_engine = AllocationEngine(config=self._config)
            logger.debug("AllocationEngine (CapitalAllocator) initialized.")
        except Exception:
            logger.warning("AllocationEngine unavailable.", exc_info=True)

    def _boot_meta_strategy_brain(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.meta_strategy.meta_brain import MetaBrain  # noqa: PLC0415
            router.meta_strategy_brain = MetaBrain(
                config=self._config,
                strategy_bank_layer=router.strategy_bank_layer,
            )
            logger.debug("MetaBrain (MetaAlphaEngine) initialized.")
        except Exception:
            logger.warning("MetaBrain unavailable.", exc_info=True)

    def _boot_strategy_diversity(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.strategy_diversity.diversity_engine import (  # noqa: PLC0415
                DiversityEngine,
            )
            router.strategy_diversity_engine = DiversityEngine(config=self._config)
            logger.debug("DiversityEngine initialized.")
        except Exception:
            logger.warning("DiversityEngine unavailable.", exc_info=True)

    def _boot_strategy_survival(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.strategy_survival.survival_engine import (  # noqa: PLC0415
                SurvivalEngine,
            )
            router.strategy_survival_engine = SurvivalEngine(
                config=self._config,
                bank_layer=router.strategy_bank_layer,
            )
            logger.debug("SurvivalEngine initialized.")
        except Exception:
            logger.warning("SurvivalEngine unavailable.", exc_info=True)

    def _boot_alpha_scanner(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.alpha_scanner.scanner_core import (  # noqa: PLC0415
                AlphaScannerCore,
            )
            router.alpha_scanner = AlphaScannerCore(
                config=self._config,
                market_data=router.market_data,
            )
            logger.debug("AlphaScannerCore initialized.")
        except Exception:
            logger.warning("AlphaScannerCore unavailable.", exc_info=True)

    def _boot_portfolio_ai(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.portfolio_ai.portfolio_ai_core import (  # noqa: PLC0415
                PortfolioAICore,
            )
            router.portfolio_ai_engine = PortfolioAICore(
                config=self._config,
                bank_layer=router.strategy_bank_layer,
                state=router.state,
            )
            logger.debug("PortfolioAICore initialized.")
        except Exception:
            logger.warning("PortfolioAICore unavailable.", exc_info=True)

    def _boot_shadow_trading(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.shadow_trading.shadow_engine import (  # noqa: PLC0415
                ShadowEngine,
            )
            router.shadow_trading_engine = ShadowEngine(
                config=self._config,
                market_data=router.market_data,
                bank_layer=router.strategy_bank_layer,
            )
            logger.debug("ShadowEngine initialized.")
        except Exception:
            logger.warning("ShadowEngine unavailable.", exc_info=True)

    def _boot_intelligence_layer(self, router: SystemRouter) -> None:
        """
        Regime detection, market pulse, event signal engine,
        adaptive learning, cognitive control, global market brain.
        """
        logger.info("[boot] intelligence layer …")
        cfg = self._config

        # Autonomous controller (regime state machine)
        try:
            from quant_ecosystem.autonomous_controller.controller import (  # noqa: PLC0415
                AutonomousController,
            )
            router.autonomous_controller = AutonomousController(config=cfg)
            logger.debug("AutonomousController initialized.")
        except Exception:
            logger.warning("AutonomousController unavailable.", exc_info=True)

        # Event bus
        try:
            from quant_ecosystem.core.event_bus import EventBus  # noqa: PLC0415
            router.event_bus = EventBus()
            logger.debug("EventBus initialized.")
        except Exception:
            logger.debug("EventBus unavailable (non-critical).")

        # Regime AI
        if getattr(cfg, "enable_regime_ai", False):
            self._boot_regime_ai(router)

        # Market Regime Detector (non-ML fallback)
        try:
            from quant_ecosystem.market_regime.regime_detector import (  # noqa: PLC0415
                RegimeDetector,
            )
            router.market_regime_detector = RegimeDetector()
            logger.debug("RegimeDetector initialized.")
        except Exception:
            logger.debug("RegimeDetector unavailable (non-critical).")

        # Event signal engine
        if getattr(cfg, "enable_event_signal_engine", False):
            self._boot_event_signal_engine(router)

        # Market pulse engine
        if getattr(cfg, "enable_market_pulse_engine", False):
            self._boot_market_pulse(router)

        # Event-driven orchestrator
        if getattr(cfg, "enable_event_driven_engine", False):
            self._boot_event_driven_orchestrator(router)

        # Adaptive learning engine
        if getattr(cfg, "enable_adaptive_learning", False):
            self._boot_adaptive_learning(router)

        # Cognitive control
        if getattr(cfg, "enable_cognitive_control", False):
            self._boot_cognitive_control(router)

        # Global market brain
        if getattr(cfg, "enable_global_market_brain", False):
            self._boot_global_market_brain(router)

    def _boot_regime_ai(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.regime_ai.regime_ai_core import (  # noqa: PLC0415
                RegimeAICore,
            )
            router.regime_ai_engine = RegimeAICore(
                config=self._config,
                model_path=getattr(self._config, "regime_ai_model_path", None),
                min_confidence=getattr(self._config, "regime_ai_min_confidence", 0.45),
            )
            logger.debug("RegimeAICore initialized.")
        except Exception:
            logger.warning("RegimeAICore unavailable.", exc_info=True)

    def _boot_event_signal_engine(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.event_signal_engine.event_driven_signal_engine import (  # noqa: PLC0415
                EventDrivenSignalEngine,
            )
            router.event_signal_engine = EventDrivenSignalEngine(
                config=self._config,
                cooldown_sec=getattr(self._config, "event_signal_engine_cooldown_sec", 20),
                max_immediate_executes=getattr(
                    self._config, "event_signal_engine_max_immediate_executes", 3
                ),
            )
            logger.debug("EventDrivenSignalEngine initialized.")
        except Exception:
            logger.warning("EventDrivenSignalEngine unavailable.", exc_info=True)

    def _boot_market_pulse(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.market_pulse.pulse_engine import (  # noqa: PLC0415
                PulseEngine,
            )
            router.market_pulse_engine = PulseEngine(
                config=self._config,
                min_strength=getattr(self._config, "market_pulse_min_strength", 0.2),
            )
            logger.debug("PulseEngine (MarketPulse) initialized.")
        except Exception:
            logger.warning("PulseEngine unavailable.", exc_info=True)

    def _boot_event_driven_orchestrator(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.event_engine.event_orchestrator import (  # noqa: PLC0415
                EventOrchestrator,
            )
            router.event_driven_orchestrator = EventOrchestrator(
                config=self._config,
                event_bus=router.event_bus,
                execution_router=router._execution_router,
            )
            logger.debug("EventOrchestrator initialized.")
        except Exception:
            logger.warning("EventOrchestrator unavailable.", exc_info=True)

    def _boot_adaptive_learning(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.adaptive_learning.learning_engine import (  # noqa: PLC0415
                LearningEngine,
            )
            router.adaptive_learning_engine = LearningEngine(config=self._config)
            logger.debug("LearningEngine (AdaptiveLearning) initialized.")
        except Exception:
            logger.warning("AdaptiveLearning unavailable.", exc_info=True)

    def _boot_cognitive_control(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.cognitive_control.cognitive_controller import (  # noqa: PLC0415
                CognitiveController,
            )
            router.cognitive_controller = CognitiveController(
                config=self._config,
                state=router.state,
                risk_engine=router.risk_engine,
            )
            logger.debug("CognitiveController initialized.")
        except Exception:
            logger.warning("CognitiveController unavailable.", exc_info=True)

    def _boot_global_market_brain(self, router: SystemRouter) -> None:
        try:
            from quant_ecosystem.global_market_brain.market_brain import (  # noqa: PLC0415
                MarketBrain,
            )
            router.global_market_brain = MarketBrain(config=self._config)
            logger.debug("MarketBrain (GlobalMarketBrain) initialized.")
        except Exception:
            logger.warning("GlobalMarketBrain unavailable.", exc_info=True)

    def _boot_safety_layer(self, router: SystemRouter) -> None:
        """Safety Governor — monitors and intervenes on abnormal conditions."""
        logger.info("[boot] safety layer …")
        cfg = self._config

        if not getattr(cfg, "enable_safety_governor", False):
            logger.debug("SafetyGovernor disabled via config.")
            return

        try:
            from quant_ecosystem.safety_governor.governor_core import (  # noqa: PLC0415
                GovernorCore,
            )
            router.safety_governor = GovernorCore(
                config=cfg,
                state=router.state,
                risk_engine=router.risk_engine,
                cooldown_sec=getattr(cfg, "safety_governor_cooldown_sec", 30.0),
                min_rejection_samples=getattr(
                    cfg, "safety_governor_min_rejection_samples", 8
                ),
            )
            logger.debug("GovernorCore (SafetyGovernor) initialized.")
        except Exception:
            logger.warning("SafetyGovernor unavailable.", exc_info=True)

    def _boot_communication_layer(self, router: SystemRouter) -> None:
        """Telegram control center — optional, config-gated."""
        logger.info("[boot] communication layer …")
        cfg = self._config

        token   = getattr(cfg, "telegram_token",   "") or ""
        chat_id = getattr(cfg, "telegram_chat_id", "") or ""

        if not token or not chat_id:
            logger.info("Telegram credentials not set — control center disabled.")
            return

        try:
            from quant_ecosystem.control.telegram_control_center import (  # noqa: PLC0415
                TelegramControlCenter,
            )
            router.telegram = TelegramControlCenter()
            # Propagate to ExecutionRouter
            if router._execution_router is not None:
                router._execution_router.telegram = router.telegram
            logger.debug("TelegramControlCenter initialized.")
        except Exception:
            logger.warning(
                "TelegramControlCenter unavailable — running without Telegram.",
                exc_info=True,
            )

    def _boot_dashboard_layer(self, router: SystemRouter) -> None:
        """Dashboard and cockpit service configs (servers are started by orchestrator)."""
        logger.info("[boot] dashboard layer …")
        cfg = self._config

        if getattr(cfg, "enable_dashboard_server", False):
            router.dashboard_service_config = {
                "enabled":            True,
                "host":               getattr(cfg, "dashboard_host",                "127.0.0.1"),
                "port":               int(getattr(cfg, "dashboard_port",            8090)),
                "update_interval_sec": float(getattr(cfg, "dashboard_update_interval_sec", 0.25)),
            }
            logger.debug(
                "Dashboard service configured: http://%s:%d",
                router.dashboard_service_config["host"],
                router.dashboard_service_config["port"],
            )

        if getattr(cfg, "enable_cockpit_server", False):
            router.cockpit_service_config = {
                "enabled":            True,
                "host":               getattr(cfg, "cockpit_host",                 "127.0.0.1"),
                "port":               int(getattr(cfg, "cockpit_port",             8091)),
                "update_interval_sec": float(getattr(cfg, "cockpit_update_interval_sec", 0.25)),
                "auth_token":         getattr(cfg, "cockpit_auth_token",           ""),
            }
            logger.debug(
                "Cockpit service configured: http://%s:%d",
                router.cockpit_service_config["host"],
                router.cockpit_service_config["port"],
            )


# ─────────────────────────────────────────────────────────────────────────────
# No-Op Broker Fallback
# ─────────────────────────────────────────────────────────────────────────────

def _make_grid_result_callback(router):
    """Return a callback that logs completed grid jobs and promotes genomes."""
    def _on_result(result) -> None:
        if not result.ok:
            logger.debug(
                "ResearchGrid job FAILED | job_id=%s type=%s error=%s",
                result.job_id[:8], result.job_type, result.error,
            )
            return

        genome_id = result.result.get("genome_id", "") if result.result else ""
        logger.info(
            "ResearchGrid job completed | job_id=%s type=%-22s genome=%-18s sharpe=%+.3f fitness=%+.3f",
            result.job_id[:8], str(result.job_type),
            (genome_id[:18] if genome_id else "—"),
            result.sharpe, result.fitness,
        )

        rg = getattr(router, "research_grid", None)
        if rg is None:
            return
        thr = getattr(rg, "promote_threshold", 0.5)
        if result.fitness >= thr and genome_id:
            lib = getattr(router, "genome_library", None)
            if lib is not None:
                try:
                    lib.store_genome(genome_id, {
                        **(result.result or {}),
                        "genome_id":    genome_id,
                        "fitness_score":result.fitness,
                        "sharpe":       result.sharpe,
                        "source":       "research_grid",
                        "job_type":     str(result.job_type),
                    })
                    logger.info(
                        "ResearchGrid genome promoted | genome_id=%s fitness=%.3f",
                        genome_id[:18], result.fitness,
                    )
                except Exception as exc:
                    logger.debug("genome_library.store_genome failed: %s", exc)
    return _on_result


class _NoOpBroker:
    """
    Silent no-op broker used when the real broker class fails to import.
    All methods return safe empty responses so the system can still boot
    and run in a degraded state without raising AttributeError.
    """

    connected    = False
    account_source = "SIMULATED"

    def place_order(self, *_: Any, **__: Any) -> dict:
        return {"status": "NOOP", "broker": "NoOp"}

    def close_position(self, *_: Any, **__: Any) -> dict:
        return {"status": "NOOP"}

    def get_balance(self) -> float:
        return 0.0

    def get_orders(self) -> list:
        return []

    def get_positions(self) -> dict:
        return {}

    def get_account_snapshot(self, **__: Any) -> dict:
        return {"equity": 0.0, "cash": 0.0, "positions": {}}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point (backward-compatible with existing callers)
# ─────────────────────────────────────────────────────────────────────────────

def build_router(config: Any) -> SystemRouter:
    """
    Public factory function.  Called by main.py (and any legacy callers)
    to assemble and return a fully wired SystemRouter.

    Args:
        config: A Config instance loaded from environment variables.

    Returns:
        A SystemRouter ready to be passed to MasterOrchestrator.
    """
    return SystemFactory(config).build()
