class AlphaCompetitionEngine:
    """
    Strategy Darwinism engine.

    Evaluates strategies using realised performance metrics sourced from
    PerformanceStore and exposes rankings for downstream consumers.
    """

    def __init__(self, strategy_registry, performance_store=None, **kwargs):

        self.strategy_registry = strategy_registry
        self.performance_store = performance_store
        self.last_results = []

    def evaluate(self):

        if not hasattr(self.strategy_registry, "get_all"):
            print("AlphaCompetition: No strategy retrieval method found.")
            return

        raw = self.strategy_registry.get_all()
        strategies = list(raw.values()) if isinstance(raw, dict) else list(raw or [])

        if not strategies:
            return

        metrics_map = self.performance_store.get_all_metrics() if self.performance_store else {}

        ranked = []
        for s in strategies:
            sid = getattr(s, "id", None) if not isinstance(s, dict) else s.get("id")
            if not sid:
                continue
            m = metrics_map.get(sid, {})
            sharpe = float(m.get("sharpe", 0.0))
            drawdown = float(m.get("drawdown", 0.0))
            win_rate = float(m.get("win_rate", 0.0))
            profit_factor = float(m.get("profit_factor", 0.0))
            dd_penalty = 1.0 + max(0.0, drawdown / 20.0)
            raw_score = sharpe * profit_factor * (win_rate / 50.0)
            score = raw_score / dd_penalty
            ranked.append(
                {
                    "strategy_id": sid,
                    "score": score,
                    "metrics": m,
                }
            )

        ranked.sort(key=lambda x: x["score"], reverse=True)
        self.last_results = ranked

        print("AlphaCompetition Top Strategies:")
        for row in ranked[:5]:
            print(row["strategy_id"], row["score"])

        return ranked

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