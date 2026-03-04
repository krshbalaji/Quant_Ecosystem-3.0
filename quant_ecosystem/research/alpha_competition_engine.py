class AlphaCompetitionEngine:
    """
    Strategy Darwinism engine.

    Strategies compete using their performance metrics.
    Top performers receive more capital allocation.
    """

    def __init__(self, strategy_registry):

        self.strategy_registry = strategy_registry
        self.last_results = []

    def evaluate(self):

        if not hasattr(self.strategy_registry, "get_all"):
            print("AlphaCompetition: No strategy retrieval method found.")
            return

        strategies = self.strategy_registry.get_all()

        if not strategies:
            return

        ranked = sorted(
            strategies,
            key=lambda s: s.get("score", 0),
            reverse=True
        )

        top = ranked[:5]

        print("AlphaCompetition Top Strategies:")

        for s in top:
            print(s.get("id"), s.get("score"))

    def capital_allocation(self):

        if not self.last_results:
            return {}

        total = sum(max(x["score"], 0) for x in self.last_results)

        if total == 0:
            return {}

        allocation = {}

        for r in self.last_results:

            strategy = r["strategy"]
            score = max(r["score"], 0)

            allocation[strategy.name] = score / total

        return allocation

    def _get_strategies(self):

        if hasattr(self.strategy_registry, "get_all"):
            return self.strategy_registry.get_all()

        if hasattr(self.strategy_registry, "strategies"):
            return list(self.strategy_registry.strategies.values())

        if hasattr(self.strategy_registry, "registry"):
            return list(self.strategy_registry.registry.values())

        print("AlphaCompetition: No strategy retrieval method found.")
        return []

    # Unified interface helper
    def run(self):
        """
        Generic entry point expected by orchestration layers.
        """
        return self.evaluate()