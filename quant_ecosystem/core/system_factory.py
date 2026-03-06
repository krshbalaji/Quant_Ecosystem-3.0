"""
Quant Ecosystem 3.0 — System Factory
Clean dependency-injection builder for all engines
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Safe constructor wrapper
# -------------------------------------------------------------------

def safe_init(cls, *args, **kwargs):
    try:
        return cls(*args, **kwargs)
    except TypeError:
        try:
            return cls()
        except Exception:
            return None
    except Exception:
        return None


# -------------------------------------------------------------------
# Router container
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# System Factory
# -------------------------------------------------------------------

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

        logger.info("SystemFactory.build() complete")

        return router


# -------------------------------------------------------------------
# CORE
# -------------------------------------------------------------------

    def _boot_core(self, router):

        logger.info("[boot] core layer")

        try:
            from quant_ecosystem.market.market_data_engine import MarketDataEngine
            router.market_data = safe_init(MarketDataEngine, config=self.config)
        except Exception:
            logger.warning("MarketDataEngine unavailable", exc_info=True)


# -------------------------------------------------------------------
# EXECUTION
# -------------------------------------------------------------------

    def _boot_execution(self, router):

        logger.info("[boot] execution layer")

        try:
            from quant_ecosystem.execution.execution_router import ExecutionRouter
            router.execution = safe_init(ExecutionRouter)
        except Exception:
            logger.error("ExecutionRouter unavailable", exc_info=True)


# -------------------------------------------------------------------
# STRATEGY
# -------------------------------------------------------------------

    def _boot_strategy(self, router):

        logger.info("[boot] strategy layer")

        try:
            from quant_ecosystem.strategies.live_strategy_engine import LiveStrategyEngine
            router.strategy_engine = safe_init(LiveStrategyEngine, config=self.config)
        except Exception:
            logger.warning("LiveStrategyEngine unavailable")

        try:
            from quant_ecosystem.strategies.strategy_bank_layer import StrategyBankLayer
            router.strategy_bank_layer = safe_init(StrategyBankLayer, config=self.config)
        except Exception:
            logger.warning("StrategyBankLayer unavailable")

        try:
            from quant_ecosystem.strategies.selector_core import SelectorCore
            router.strategy_selector = safe_init(SelectorCore, config=self.config)
        except Exception:
            logger.warning("SelectorCore unavailable")

        try:
            from quant_ecosystem.capital_allocator.allocation_engine import AllocationEngine
            router.capital_allocator_engine = safe_init(AllocationEngine, config=self.config)
        except Exception:
            logger.warning("AllocationEngine unavailable")

        try:
            from quant_ecosystem.strategy_diversity.diversity_engine import DiversityEngine
            router.strategy_diversity_engine = safe_init(DiversityEngine, config=self.config)
        except Exception:
            logger.warning("DiversityEngine unavailable")

        try:
            from quant_ecosystem.strategy_survival.survival_engine import SurvivalEngine
            router.strategy_survival_engine = safe_init(SurvivalEngine, config=self.config)
        except Exception:
            logger.warning("SurvivalEngine unavailable")

        try:
            from quant_ecosystem.alpha_scanner.alpha_scanner_core import AlphaScannerCore
            router.alpha_scanner = safe_init(AlphaScannerCore, config=self.config)
        except Exception:
            logger.warning("AlphaScannerCore unavailable")

        try:
            from quant_ecosystem.shadow_trading.shadow_engine import ShadowEngine
            router.shadow_trading_engine = safe_init(ShadowEngine, config=self.config)
        except Exception:
            logger.warning("ShadowEngine unavailable")


# -------------------------------------------------------------------
# INTELLIGENCE
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# SAFETY
# -------------------------------------------------------------------

    def _boot_safety(self, router):

        logger.info("[boot] safety layer")

        try:
            from quant_ecosystem.safety_governer.governor_core import GovernorCore
            router.safety_governor = safe_init(GovernorCore, config=self.config)
        except Exception:
            logger.warning("GovernorCore unavailable")


# -------------------------------------------------------------------
# TELEGRAM
# -------------------------------------------------------------------

    def _boot_communication(self, router):

        logger.info("[boot] communication layer")

        try:
            from quant_ecosystem.control.telegram_control_center import TelegramControlCenter
            router.telegram = safe_init(TelegramControlCenter, config=self.config)
        except Exception:
            logger.warning("TelegramControlCenter unavailable")