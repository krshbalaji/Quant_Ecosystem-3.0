import logging
import inspect

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyRegistry:

    def __init__(self):
        self._strategies = {}

    def register(self, strategy):
        try:
            stored_strategy = self._normalize_strategy(strategy)
            sid = getattr(stored_strategy, "STRATEGY_ID", stored_strategy.__class__.__name__)
            stored_strategy.id = sid
            self._strategies[sid] = stored_strategy

            logger.info("Strategy registered: %s", sid)
            return stored_strategy

        except Exception as e:
            logger.warning("Strategy registration failed: %s", e)
            return None

    def _normalize_strategy(self, strategy):
        if inspect.isclass(strategy):
            if not issubclass(strategy, BaseStrategy):
                raise TypeError(f"Unsupported strategy class: {strategy}")
            return strategy()

        if isinstance(strategy, BaseStrategy):
            return strategy

        sid = getattr(strategy, "STRATEGY_ID", None)
        if sid is None:
            raise AttributeError("Strategy must expose STRATEGY_ID")

        strategy.id = sid

        return strategy

    def load(self):
        """Return strategies for LiveStrategyEngine"""
        return list(self._strategies.values())

    def get(self, sid):
        return self._strategies.get(sid)

    def all(self):
        return list(self._strategies.values())

    def count(self):
        return len(self._strategies)
