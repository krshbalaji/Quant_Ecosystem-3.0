from __future__ import annotations
import logging
from typing import Dict, List, Optional

from quant_ecosystem.strategy_selector.activation_manager import ActivationManager
from quant_ecosystem.strategy_selector.performance_ranker import PerformanceRanker
from quant_ecosystem.strategy_selector.regime_strategy_map import RegimeStrategyMap

logger = logging.getLogger(__name__)


class AutonomousStrategySelector:

    def __init__(
        self,
        strategy_bank_layer=None,
        strategy_engine=None,
        strategy_bank_engine=None,
        regime_source=None,
        ranker: Optional[PerformanceRanker] = None,
        regime_map: Optional[RegimeStrategyMap] = None,
        activation_manager: Optional[ActivationManager] = None,
        max_active_strategies: int = 5,
        **kwargs
    ):

        self.strategy_bank_layer = strategy_bank_layer
        self.strategy_engine = strategy_engine
        self.strategy_bank_engine = strategy_bank_engine
        self.regime_source = regime_source

        self.ranker = ranker or PerformanceRanker()
        self.regime_map = regime_map or RegimeStrategyMap()

        self.activation_manager = activation_manager or ActivationManager(
            strategy_engine=strategy_engine,
            strategy_bank_engine=strategy_bank_engine,
            max_active_strategies=max_active_strategies,
        )

        self.max_active_strategies = max(1, int(max_active_strategies))

    def select(self, strategies: list, regime: str = "UNKNOWN") -> list:

        if not strategies:
            return []

        ranked = sorted(
            strategies,
            key=lambda s: s.get("metrics", {}).get("fitness_score", 0),
            reverse=True
        )

        return ranked[: self.max_active_strategies]


class SelectorCore:

    def __init__(self, **kwargs):

        self._log = logging.getLogger(__name__)

        try:
            self._delegate = AutonomousStrategySelector(**kwargs)
        except Exception as exc:
            self._log.warning(
                "SelectorCore: delegate unavailable (%s) — stub mode", exc
            )
            self._delegate = None

        self._log.info("SelectorCore initialized")

    def select(self, strategies: list, regime: str = "UNKNOWN") -> list:

        if self._delegate:

            try:
                return self._delegate.select(strategies, regime)

            except Exception as exc:

                self._log.warning(
                    "SelectorCore.select error (%s)", exc
                )

        return strategies