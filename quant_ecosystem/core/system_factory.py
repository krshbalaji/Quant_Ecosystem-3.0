"""
Quant Ecosystem 3.0 — System Factory
Clean dependency injection builder
"""

from __future__ import annotations

import logging
import importlib

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# SAFE INIT
# ---------------------------------------------------------

def safe_init(cls, *args, **kwargs):
    """
    Safe constructor wrapper.
    Allows missing config parameters.
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


# ---------------------------------------------------------
# ROUTER
# ---------------------------------------------------------

class SystemRouter:

    def __init__(self, config):

        self.config = config

        # core
        self.market_data = None
        self.state = None

        # execution
        self.execution = None
        self.risk_engine = None

        # strategy
        self.strategy_engine = None
        self.strategy_bank_layer = None
        self.strategy_selector = None
        self.capital_allocator_engine = None
        self.strategy_diversity_engine = None
        self.strategy_survival_engine = None

        # alpha
        self.alpha_scanner = None

        # intelligence
        self.global_intelligence = None
        self.autonomous_controller = None
        self.regime_ai_engine = None

        # shadow
        self.shadow_trading_engine = None

        # safety
        self.safety_governor = None

        # communication
        self.telegram = None


# ---------------------------------------------------------
# FACTORY
# ---------------------------------------------------------

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

        # post boot wiring
        if router.global_intelligence and router.market_data:
            try:
                router.global_intelligence.set_market_data(router.market_data)
            except Exception:
                pass

        logger.info("SystemFactory.build() complete")

        return router


# ---------------------------------------------------------
# CORE
# ---------------------------------------------------------

    def _boot_core(self, router):

        logger.info("[boot] core layer")

        try:
            from quant_ecosystem.market.market_data_engine import MarketDataEngine

            router.market_data = safe_init(
                MarketDataEngine,
                config=self.config
            )

        except Exception:
            logger.warning("MarketDataEngine unavailable", exc_info=True)


# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

    def _boot_execution(self, router):

        logger.info("[boot] execution layer")

        try:

            from quant_ecosystem.execution.execution_router import ExecutionRouter

            router.execution = safe_init(ExecutionRouter)

        except Exception:
            logger.error("ExecutionRouter unavailable", exc_info=True)


# ---------------------------------------------------------
# STRATEGY
# ---------------------------------------------------------

    def _boot_strategy(self, router):

        logger.info("[boot] strategy layer")

        engines = [

            ("LiveStrategyEngine",
             "quant_ecosystem.strategies.live_strategy_engine",
             "strategy_engine"),

            ("StrategyBankLayer",
             "quant_ecosystem.strategies.strategy_bank_layer",
             "strategy_bank_layer"),

            ("SelectorCore",
             "quant_ecosystem.strategies.selector_core",
             "strategy_selector"),

            ("AllocationEngine",
             "quant_ecosystem.capital_allocator.allocation_engine",
             "capital_allocator_engine"),

            ("DiversityEngine",
             "quant_ecosystem.strategy_diversity.diversity_engine",
             "strategy_diversity_engine"),

            ("SurvivalEngine",
             "quant_ecosystem.strategy_survival.survival_engine",
             "strategy_survival_engine"),
        ]

        for cls_name, mod_path, attr in engines:

            try:

                mod = importlib.import_module(mod_path)

                cls = getattr(mod, cls_name)

                setattr(router, attr, safe_init(cls, config=self.config))

            except Exception:

                logger.warning("%s unavailable", cls_name)


        # alpha scanner
        try:
            from quant_ecosystem.alpha_scanner.scanner_core import GlobalAlphaScanner
            router.alpha_scanner = safe_init(GlobalAlphaScanner)
        except Exception:
            logger.warning("GlobalAlphaScanner unavailable")

        # shadow trading
        try:
            from quant_ecosystem.shadow_trading.shadow_engine import ShadowTradingEngine
            router.shadow_trading_engine = safe_init(ShadowTradingEngine)
        except Exception:
            logger.warning("ShadowTradingEngine unavailable")


# ---------------------------------------------------------
# INTELLIGENCE
# ---------------------------------------------------------

    def _boot_intelligence(self, router):

        logger.info("[boot] intelligence layer")

        try:

            from quant_ecosystem.intelligence.global_intelligence_engine import GlobalIntelligenceEngine

            router.global_intelligence = safe_init(
                GlobalIntelligenceEngine,
                config=self.config
            )

        except Exception:
            logger.warning("GlobalIntelligenceEngine unavailable")

        try:

            from quant_ecosystem.autonomous_controller.autonomous_controller import AutonomousController

            router.autonomous_controller = safe_init(
                AutonomousController,
                config=self.config
            )

        except Exception:
            logger.warning("AutonomousController unavailable")

        try:

            from quant_ecosystem.regime_ai.regime_ai_core import RegimeAICore

            router.regime_ai_engine = safe_init(
                RegimeAICore,
                config=self.config
            )

        except Exception:
            logger.warning("RegimeAICore unavailable")


# ---------------------------------------------------------
# SAFETY
# ---------------------------------------------------------

    def _boot_safety(self, router):

        logger.info("[boot] safety layer")

        try:

            from quant_ecosystem.safety_governor.governor_core import GovernorCore

            router.safety_governor = safe_init(
                GovernorCore,
                config=self.config
            )

        except Exception:
            logger.warning("GovernorCore unavailable")


# ---------------------------------------------------------
# TELEGRAM
# ---------------------------------------------------------

    def _boot_communication(self, router):

        logger.info("[boot] communication layer")

        try:

            from quant_ecosystem.control.telegram_control_center import TelegramControlCenter

            router.telegram = safe_init(
                TelegramControlCenter,
                config=self.config
            )

        except Exception:
            logger.warning("TelegramControlCenter unavailable")