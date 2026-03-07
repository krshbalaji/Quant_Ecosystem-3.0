import random

class AlphaDiscoveryEngine:

    def __init__(self, strategy_registry, backtest_engine=None, **kwargs):
        self.strategy_registry = strategy_registry
        self.backtest_engine = backtest_engine

    def discover(self):

        strategies = self.strategy_registry.get_all()

        discovered = []

        # registry may return dict or list
        if isinstance(strategies, dict):
            iterable = strategies.items()
        else:
            iterable = [(s.get("id", "unknown"), s) for s in strategies]

        for strategy_id, entry in iterable:

            strategy = entry.get("strategy") if isinstance(entry, dict) else entry

            if strategy is None:
                continue

            try:
                score = getattr(strategy, "score", None)
                discovered.append((strategy_id, score))
            except Exception:
                continue

        print(f"AlphaDiscovery: evaluated {len(discovered)} strategies")

        return discovered

    def run(self):
        return self.discover()