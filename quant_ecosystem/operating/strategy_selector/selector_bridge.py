class SelectorBridge:

    def __init__(self, registry, selector):
        self.registry = registry
        self.selector = selector

    def get_best_strategy(self, regime):

        strategies = self.registry.get_all()

        if not strategies:
            return None

        from quant_ecosystem.operating.strategy_selector.strategy_guard import StrategyGuard
        from quant_ecosystem.operating.strategy_selector.ai_selector import AISelector

        guard = StrategyGuard()
        disabled = guard.evaluate()

        strategy_list = [
            s for s in strategies
            if getattr(s, "name", None) not in disabled
        ]

        ai = AISelector()
        best = ai.select(strategy_list, regime)

        return best