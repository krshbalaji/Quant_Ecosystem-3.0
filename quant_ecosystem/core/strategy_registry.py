from __future__ import annotations

from typing import Dict, List, Union

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy


class StrategyRegistry:
    """
    Institutional strategy registry for class-based strategies.
    """

    def __init__(self) -> None:
        self._strategies: Dict[str, BaseStrategy] = {}

    def register(self, strategy: Union[BaseStrategy, Dict[str, object], object]) -> None:
        """
        Register a strategy.

        Preferred usage is to pass a BaseStrategy instance. A legacy
        dict payload is also accepted and will be wrapped into a
        minimal BaseStrategy-compatible object to keep the registry
        free of raw dictionaries.
        """
        if isinstance(strategy, BaseStrategy) or hasattr(strategy, "id"):
            self._strategies[strategy.id] = strategy
            return
        if not isinstance(strategy, dict):
            raise TypeError("Strategy must be a BaseStrategy-like object or dict-compatible payload.")

        sid = str(strategy.get("id"))
        name = str(strategy.get("name", sid))
        family = str(strategy.get("family", "research"))
        params = dict(strategy.get("parameters") or strategy.get("params") or {})

        class _DiscoveredStrategy(BaseStrategy):
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

    def get(self, strategy_id: str) -> BaseStrategy | None:
        return self._strategies.get(strategy_id)

    def get_all(self) -> Dict[str, BaseStrategy]:
        return dict(self._strategies)

    def list_by_family(self, family_name: str) -> List[BaseStrategy]:
        family = family_name.lower().strip()
        return [s for s in self._strategies.values() if s.family.lower() == family]

    def count(self) -> int:
        return len(self._strategies)
