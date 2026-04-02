import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Registry that stores all promoted strategies.
    Used by LiveStrategyEngine to load active strategies.
    """

    def __init__(self):
        self._strategies: Dict[str, Any] = {}
        logger.info("StrategyRegistry initialized")

    def load(self):
        return list(self._strategies.values())
    
    def register(self, name: str, strategy: Any) -> None:
        self._strategies[name] = strategy
        logger.info("Strategy registered: %s", name)

    def unregister(self, name: str) -> None:
        if name in self._strategies:
            del self._strategies[name]

    def get(self, name: str):
        return self._strategies.get(name)

    def list(self):
        return list(self._strategies.keys())

    def load(self):
        """
        LiveStrategyEngine expects this method.
        Returns all strategies currently registered.
        """
        return list(self._strategies.values())

    def clear(self):
        self._strategies.clear()

        