class AlphaEvolutionMemory:

    def __init__(self):
        self._strategies = {}

    def record(
        self,
        strategy_id,
        win_rate,
        sharpe,
        pnl,
    ):
        self._strategies[strategy_id] = {
            "win_rate": win_rate,
            "sharpe": sharpe,
            "pnl": pnl,
        }

    def fetch(
        self,
        strategy_id,
    ):
        return self._strategies.get(
            strategy_id
        )

    def rank(
        self,
    ):
        ranked = sorted(
            self._strategies.items(),
            key=lambda x: (
                x[1]["sharpe"],
                x[1]["pnl"],
            ),
            reverse=True,
        )

        return ranked

    def clear(self):
        self._strategies.clear()


alpha_evolution_memory = (
    AlphaEvolutionMemory()
)