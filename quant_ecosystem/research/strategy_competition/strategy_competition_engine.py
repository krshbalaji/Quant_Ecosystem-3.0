class StrategyCompetitionEngine:

    def __init__(self):
        self.league_table = {}

    def update(self, strategy_id, metrics):
        self.league_table[strategy_id] = metrics

    def rank(self):
        return sorted(
            self.league_table.items(),
            key=lambda x: x[1]["sharpe"],
            reverse=True
        )

    def allocate_capital(self):
        ranked = self.rank()
        allocations = {}

        total = len(ranked)
        for i, (sid, _) in enumerate(ranked):
            allocations[sid] = 1 / total

        return allocations