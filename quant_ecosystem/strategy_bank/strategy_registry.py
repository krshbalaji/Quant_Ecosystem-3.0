"""
quant_ecosystem/core/strategy_registry.py
==========================================
Institutional strategy registry for class-based strategies.

LiveStrategyEngine calls ``registry.load()`` at construction time to
populate its active strategy table.  This registry exposes a ``load()``
method that returns the current registry contents (and performs an initial
auto-discovery pass if the registry is still empty).
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

try:
    from quant_ecosystem.strategies.base.base_strategy import BaseStrategy
except Exception:  # pragma: no cover
    BaseStrategy = object  # type: ignore[misc,assignment]


class StrategyRegistry:
    """
    Institutional strategy registry for class-based strategies.

    Strategies can be registered explicitly via ``register()`` or
    discovered automatically by scanning a Python package via ``load()``.
    """

    def __init__(self, strategy_path: str = "quant_ecosystem.strategies", **kwargs) -> None:
        self.strategy_path = strategy_path
        self._strategies: Dict[str, object] = {}

    # ------------------------------------------------------------------
    # Auto-discovery
    # ------------------------------------------------------------------

        import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)


class StrategyRegistry:

    def __init__(self):
        self._strategies = None

    def load(self):

        if self._strategies is not None:
            return self._strategies

        strategies = {}

        try:
            package = importlib.import_module("quant_ecosystem.strategies")

            for _, module_name, _ in pkgutil.walk_packages(package.__path__):

                module = importlib.import_module(
                    f"quant_ecosystem.strategies.{module_name}"
                )

                if getattr(module, "IS_STRATEGY", False):
                    strategies[module_name] = module

        except Exception as e:
            logger.warning(f"Strategy discovery failed: {e}")

        self._strategies = strategies
        return strategies

    def all(self):
        return self.load()

    # ------------------------------------------------------------------
    # Explicit registration
    # ------------------------------------------------------------------

    def register(self, strategy: Union[object, Dict[str, object]]) -> None:
        """
        Register a strategy explicitly.

        Preferred usage is to pass a BaseStrategy instance.  A legacy
        dict payload is also accepted and will be wrapped into a minimal
        BaseStrategy-compatible object to keep the registry free of raw
        dictionaries.
        """
        # Prefer object with .id attribute (BaseStrategy-like)
        if hasattr(strategy, "id"):
            self._strategies[strategy.id] = strategy
            return

        if not isinstance(strategy, dict):
            name = getattr(strategy, "__name__", str(strategy))
            self._strategies[name] = strategy
            return

        # Dict payload — wrap into a minimal strategy-compatible object
        sid    = str(strategy.get("id", ""))
        name   = str(strategy.get("name", sid))
        family = str(strategy.get("family", "research"))
        params = dict(strategy.get("parameters") or strategy.get("params") or {})

        try:
            from quant_ecosystem.strategies.base.base_strategy import BaseStrategy as _BS

            class _DiscoveredStrategy(_BS):
                def generate_signal(self, market_data):
                    return None

            obj = _DiscoveredStrategy(
                id=sid,
                name=name,
                family=family,
                params=params,
                required_timeframes=["1d"],
                required_symbols=[],
            )
            self._strategies[obj.id] = obj
        except Exception:
            if sid:
                self._strategies[sid] = strategy

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, strategy_id: str) -> Optional[object]:
        return self._strategies.get(strategy_id)

    def get_all(self) -> Dict[str, object]:
        return dict(self._strategies)

    def all(self) -> List[object]:
        """Return all registered strategy objects as a list."""
        return list(self._strategies.values())

    def list_by_family(self, family_name: str) -> List[object]:
        family = family_name.lower().strip()
        return [
            s for s in self._strategies.values()
            if getattr(s, "family", "").lower() == family
        ]

    def count(self) -> int:
        return len(self._strategies)

    def __len__(self) -> int:
        return len(self._strategies)

    def __repr__(self) -> str:
        return f"StrategyRegistry(count={len(self)}, path={self.strategy_path!r})"
