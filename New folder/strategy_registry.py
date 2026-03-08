from pathlib import Path
import importlib.util
import logging

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Loads strategies dynamically from strategy folders.
    """

    def __init__(self, strategy_path="quant_ecosystem/strategies"):
        self.path = Path(strategy_path)
        self.strategies = {}

    def _safe_load_strategy(self, file_path):
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "strategy"):
                return module.strategy

        except Exception as e:
            logger.warning(f"Failed to load strategy {file_path}: {e}")

        return None

    def load(self):
        """
        Load strategies from disk.
        """

        strategies = {}

        if not self.path.exists():
            logger.warning("Strategy directory not found")
            return strategies

        for file in self.path.glob("*.py"):

            strategy_fn = self._safe_load_strategy(file)

            if strategy_fn:
                strategies[file.stem] = strategy_fn

        self.strategies = strategies

        logger.info(f"{len(strategies)} strategies loaded")

        return strategies

    def list(self):
        return list(self.strategies.values())

    def get(self, name):
        return self.strategies.get(name)