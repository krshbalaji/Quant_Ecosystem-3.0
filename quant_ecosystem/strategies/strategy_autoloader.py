import importlib
import inspect
import logging
import pkgutil
from types import ModuleType

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

STRATEGY_PACKAGES = (
    "quant_ecosystem.strategies.mean_reversion",
    "quant_ecosystem.strategies.momentum",
    "quant_ecosystem.strategies.trend",
    "quant_ecosystem.strategies.volatility",
    "quant_ecosystem.strategies.microstructure",
    "quant_ecosystem.strategies.generated",
)


def _iter_strategy_modules(package_name: str):
    try:
        package = importlib.import_module(package_name)
    except Exception:
        logger.exception("[strategy_loader] package load failed: %s", package_name)
        return

    yield from _walk_package(package)


def _walk_package(package: ModuleType):
    package_paths = getattr(package, "__path__", None)
    if not package_paths:
        logger.warning("[strategy_loader] package missing __path__: %s", package.__name__)
        return

    for _, module_name, _ in pkgutil.walk_packages(package_paths, prefix=f"{package.__name__}."):
        try:
            yield importlib.import_module(module_name)
        except Exception:
            logger.exception("[strategy_loader] module import failed: %s", module_name)


def _iter_strategy_classes(module: ModuleType):
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if not issubclass(obj, BaseStrategy) or obj is BaseStrategy:
            continue
        strategy_id = getattr(obj, "STRATEGY_ID", None)
        if not strategy_id:
            logger.warning("[strategy_loader] skipping strategy without STRATEGY_ID: %s.%s", module.__name__, obj.__name__)
            continue
        yield obj


def auto_register(registry):
    total = 0

    for package_name in STRATEGY_PACKAGES:
        for module in _iter_strategy_modules(package_name):
            for strategy_class in _iter_strategy_classes(module):
                try:
                    stored_strategy = registry.register(strategy_class)
                    if stored_strategy is None:
                        continue
                    total += 1
                    logger.info("[strategy_loader] auto-registered strategy: %s", strategy_class.STRATEGY_ID)
                except Exception:
                    logger.exception(
                        "[strategy_loader] registration failed for %s.%s",
                        module.__name__,
                        strategy_class.__name__,
                    )

    logger.info("[strategy_loader] autoload complete: %d strategies registered", total)
    return total
