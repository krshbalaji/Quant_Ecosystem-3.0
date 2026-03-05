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

        raw = self.strategy_registry.get_all()
        strategies = list(raw.values()) if isinstance(raw, dict) else list(raw or [])

        if not strategies:
            return

        def _score(item):
            if isinstance(item, dict):
                return item.get("score", 0)
            return getattr(item, "score", 0)

        ranked = sorted(strategies, key=_score, reverse=True)
        top = ranked[:5]

        print("AlphaCompetition Top Strategies:")

        for s in top:
            if isinstance(s, dict):
                sid = s.get("id")
                score = s.get("score")
            else:
                sid = getattr(s, "id", None)
                score = getattr(s, "score", None)
            print(sid, score)

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