import importlib.util
from pathlib import Path


class StrategyRegistry:

    def __init__(self):
        self.path = Path("strategy_bank/validated")
        self.path.mkdir(parents=True, exist_ok=True)

    def load(self):
        strategies = []
        for file in sorted(self.path.glob("*.py")):
            strategy_fn = self._safe_load_strategy(file)
            if strategy_fn:
                strategies.append(
                    {
                        "id": file.stem,
                        "name": file.stem,
                        "callable": strategy_fn,
                        "supported_regimes": self._supported_regimes(file),
                    }
                )
        return strategies

    def _safe_load_strategy(self, path):
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            strategy_fn = getattr(module, "strategy", None)
            if callable(strategy_fn):
                return strategy_fn
        except Exception:
            return None
        return None

    def _supported_regimes(self, path):
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if not spec or not spec.loader:
                return ["TREND", "MEAN_REVERSION", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS"]
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            regimes = getattr(module, "SUPPORTED_REGIMES", None)
            if isinstance(regimes, (list, tuple)) and regimes:
                return [str(item).upper() for item in regimes]
        except Exception:
            pass
        return ["TREND", "MEAN_REVERSION", "HIGH_VOLATILITY", "LOW_VOLATILITY", "CRISIS"]
