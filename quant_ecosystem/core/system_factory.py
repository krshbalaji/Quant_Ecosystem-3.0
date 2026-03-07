"""
Quant Ecosystem 3.0 — System Factory
Clean dependency-injection builder for all engines.

PATCH CHANGES
─────────────
Fix 3: ExecutionRouter instantiated without config= (it self-loads config
       via _load_config). Passing config= raises unexpected-keyword-arg TypeError.

Fix 5: All optional engine boots wrapped in individual try/except.
       Boot continues fully in PAPER mode even if optional engines are absent.

Fix (import paths):
  • safety_governer (typo) → safety_governor
  • AlphaScannerCore        → GlobalAlphaScanner (scanner_core.py)
  • ShadowEngine            → ShadowTradingEngine (shadow_engine.py)

Fix (post-boot wiring):
  • market_data injected into global_intelligence after both are built.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def safe_init(cls, *args, **kwargs):
    """
    Attempt cls(**kwargs); on TypeError retry cls().
    Returns None on any failure so boot always continues.
    """
    try:
        return cls(*args, **kwargs)
    except TypeError:
        try:
            return cls()
        except Exception as exc:
            logger.warning("safe_init fallback failed for %s: %s", cls.__name__, exc)
            return None
    except Exception as exc:
        logger.warning("safe_init failed for %s: %s", cls.__name__, exc)
        return None


class SystemRouter:

    def __init__(self, config):
        self.config = config
        self.market_data             = None
        self.state                   = None
        self.execution               = None
        self.risk_engine             = None
        self.strategy_engine         = None
        self.strategy_bank_layer     = None
        self.strategy_selector       = None
        self.capital_allocator_engine = None
        self.strategy_diversity_engine = None
        self.strategy_survival_engine  = None
        self.alpha_scanner           = None
        self.global_intelligence     = None
        self.autonomous_controller   = None
        self.regime_ai_engine        = None
        self.shadow_trading_engine   = None
        self.safety_governor         = None
        self.telegram                = None
        self.research_memory         = None
        self.genome_library          = None
        self.trading_enabled = True

    # ---------------------------
    # TELEGRAM REPORT INTERFACE
    # ---------------------------

    def get_strategy_report(self):
        if self.strategy_engine and hasattr(self.strategy_engine, "strategies"):
            names = list(self.strategy_engine.strategies.keys())
            return "Strategies: " + ", ".join(names[:10])
        return "Strategy engine not ready."

    def get_positions_report(self):
        return "Positions report not implemented yet."

    def get_dashboard_report(self):
        return "Dashboard not ready yet."

    def get_status_report(self):
        enabled = getattr(self, "trading_enabled", True)
        return f"System status | trading_enabled={enabled}"
    
    def set_trading_mode(self, mode: str):
        mode = str(mode).upper()

        if mode not in ("PAPER", "LIVE"):
            return f"Invalid trading mode: {mode}"

        self.config.mode = mode

        if hasattr(self, "execution_router") and self.execution_router:
            try:
                self.execution_router.mode = mode
            except Exception:
                pass

        return f"Trading mode set to {mode}"
    
    # ---- TELEGRAM CONTROL METHODS ----

    def start_trading(self):
        self.trading_enabled = True
        return "Trading started."

    def stop_trading(self):
        self.trading_enabled = False
        return "Trading stopped."

    def kill_switch(self):
        self.trading_enabled = False
        return "Emergency kill switch activated."

    def set_auto_mode(self, enabled: bool):
        self.trading_enabled = bool(enabled)
        return f"Auto mode set to {enabled}"

    def get_status_report(self):
        return f"Trading enabled: {self.trading_enabled}"

    def get_positions_report(self):
        return "Positions report not yet implemented."

    def get_dashboard_report(self):
        return "Dashboard report placeholder."

    def get_risk_report(self):
        return "Risk report placeholder"
class SystemFactory:

    def __init__(self, config):
        self.config = config

    def build(self):
        router = SystemRouter(self.config)
        logger.info("SystemFactory.build() starting")

        self._boot_core(router)
        self._boot_execution(router)
        self._boot_strategy(router)
        self._boot_intelligence(router)
        self._boot_safety(router)
        self._boot_communication(router)
        self._boot_research_memory(router)
        self._boot_genome_memory(router)
        self._boot_autonomous_lab(router)

        # Post-boot wiring: inject market_data into global_intelligence
        if router.global_intelligence and router.market_data:
            try:
                router.global_intelligence.set_market_data(router.market_data)
            except Exception:
                pass

        logger.info("SystemFactory.build() complete")
        return router

    def _boot_autonomous_lab(self, router):

        logger.info("[boot] autonomous strategy lab")

        try:
            from quant_ecosystem.autonomous_lab.strategy_discovery_engine import StrategyDiscoveryEngine

            router.strategy_discovery_engine = StrategyDiscoveryEngine(router)

        except Exception as e:
            logger.warning(f"Autonomous lab unavailable: {e}")
    
    def _boot_core(self, router):
        logger.info("[boot] core layer")
        try:
            from quant_ecosystem.market.market_data_engine import MarketDataEngine
            router.market_data = safe_init(MarketDataEngine, config=self.config)
        except Exception:
            logger.warning("MarketDataEngine unavailable", exc_info=True)

    def _boot_execution(self, router):
        logger.info("[boot] execution layer")
        # FIX 3: ExecutionRouter has no `config` param — do NOT pass it.
        try:
            from quant_ecosystem.execution.execution_router import ExecutionRouter
            router.execution = safe_init(ExecutionRouter)
        except Exception:
            logger.error("ExecutionRouter unavailable", exc_info=True)

    def _boot_strategy(self, router):
        logger.info("[boot] strategy layer")
        for cls_name, mod_path in [
            ("LiveStrategyEngine",  "quant_ecosystem.strategies.live_strategy_engine"),
            ("StrategyBankLayer",   "quant_ecosystem.strategies.strategy_bank_layer"),
            ("SelectorCore",        "quant_ecosystem.strategies.selector_core"),
            ("AllocationEngine",    "quant_ecosystem.capital_allocator.allocation_engine"),
            ("DiversityEngine",     "quant_ecosystem.strategy_diversity.diversity_engine"),
            ("SurvivalEngine",      "quant_ecosystem.strategy_survival.survival_engine"),
        ]:
            try:
                import importlib
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                obj = safe_init(cls, config=self.config)
                attr_map = {
                    "LiveStrategyEngine":  "strategy_engine",
                    "StrategyBankLayer":   "strategy_bank_layer",
                    "SelectorCore":        "strategy_selector",
                    "AllocationEngine":    "capital_allocator_engine",
                    "DiversityEngine":     "strategy_diversity_engine",
                    "SurvivalEngine":      "strategy_survival_engine",
                }
                setattr(router, attr_map[cls_name], obj)
            except Exception:
                logger.warning("%s unavailable", cls_name)

        # FIX (class name): GlobalAlphaScanner, not AlphaScannerCore
        try:
            from quant_ecosystem.alpha_scanner.scanner_core import GlobalAlphaScanner
            router.alpha_scanner = safe_init(GlobalAlphaScanner)
        except Exception:
            logger.warning("GlobalAlphaScanner unavailable")

        # FIX (class name): ShadowTradingEngine, not ShadowEngine
        try:
            from quant_ecosystem.shadow_trading.shadow_engine import ShadowTradingEngine
            router.shadow_trading_engine = safe_init(ShadowTradingEngine)
        except Exception:
            logger.warning("ShadowTradingEngine unavailable")

    def _boot_intelligence(self, router):
        logger.info("[boot] intelligence layer")
        try:
            from quant_ecosystem.intelligence.global_intelligence_engine import GlobalIntelligenceEngine
            router.global_intelligence = safe_init(GlobalIntelligenceEngine, config=self.config)
        except Exception:
            logger.warning("GlobalIntelligenceEngine unavailable")
        try:
            from quant_ecosystem.autonomous_controller.autonomous_controller import AutonomousController
            router.autonomous_controller = safe_init(AutonomousController, config=self.config)
        except Exception:
            logger.warning("AutonomousController unavailable")
        try:
            from quant_ecosystem.regime_ai.regime_ai_core import RegimeAICore
            router.regime_ai_engine = safe_init(RegimeAICore, config=self.config)
        except Exception:
            logger.warning("RegimeAICore unavailable")

    def _boot_safety(self, router):
        logger.info("[boot] safety layer")
        # FIX (typo): was 'safety_governer' → 'safety_governor'
        try:
            from quant_ecosystem.safety_governor.governor_core import GovernorCore
            router.safety_governor = safe_init(GovernorCore, config=self.config)
        except Exception:
            logger.warning("GovernorCore unavailable")

    def _boot_communication(self, router):
        logger.info("[boot] communication layer")
        try:
            from quant_ecosystem.control.telegram_controller import TelegramController
            router.telegram = safe_init(
                TelegramController,
                config=self.config
            )

            if router.telegram:
                router.telegram.bind_router(router)

        except Exception:
            logger.warning("TelegramControlCenter unavailable")

    def _boot_research_memory(self, router):
        logger.info("[boot] research memory layer")
        try:
            from quant_ecosystem.research_memory.layer import ResearchMemoryLayer
            router.research_memory = ResearchMemoryLayer(config=self.config)
        except Exception:
            logger.warning("ResearchMemoryLayer unavailable")

    def _boot_genome_memory(self, router):
        """Wire ResearchMemoryLayer into all genome engines that were already booted."""
        logger.info("[boot] genome memory integration")
        try:
            from quant_ecosystem.alpha_genome.genome_library import GenomeLibrary
            router.genome_library = GenomeLibrary(
                research_memory=router.research_memory
            )
        except Exception:
            pass

        if router.research_memory is None:
            return

        # Inject into each genome engine if it exists on the router
        rm  = router.research_memory
        lib = getattr(router, "genome_library", None)

        for attr in ("genome_generator", "genome_mutator", "genome_crossbreeder", "genome_evaluator"):
            obj = getattr(router, attr, None)
            if obj is None:
                continue
            try:
                if hasattr(obj, "set_research_memory"):
                    if attr in ("genome_generator", "genome_evaluator"):
                        obj.set_research_memory(rm, genome_library=lib)
                    else:
                        obj.set_research_memory(rm)
            except Exception:
                pass

        # Also inject into alpha_mutation_engine and alpha_crossover_engine
        # which wrap the primitive engines — they inherit via _mutator / _base_crossbreeder
        for attr in ("alpha_mutation_engine", "alpha_crossover_engine"):
            obj = getattr(router, attr, None)
            if obj is None:
                continue
            try:
                inner_mutator = getattr(obj, "_mutator", None)
                if inner_mutator and hasattr(inner_mutator, "set_research_memory"):
                    inner_mutator.set_research_memory(rm)
                inner_xbreeder = getattr(obj, "_base_crossbreeder", None)
                if inner_xbreeder and hasattr(inner_xbreeder, "set_research_memory"):
                    inner_xbreeder.set_research_memory(rm)
            except Exception:
                pass

