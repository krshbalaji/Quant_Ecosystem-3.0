import time
import numpy as np


class AlphaCompetitionEngine:

    def __init__(
        self,
        strategy_registry,
        portfolio_engine,
        evaluation_interval=120,
        min_trades=30,
        retirement_sharpe=0.3,
        promotion_sharpe=1.2, **kwargs
    ):

        self.registry = strategy_registry
        self.portfolio = portfolio_engine

        self.interval = evaluation_interval
        self.min_trades = min_trades

        self.retirement_sharpe = retirement_sharpe
        self.promotion_sharpe = promotion_sharpe

        self.last_run = 0

    def start(self):

        print("Alpha Competition Engine started.")

    def evaluate(self):

        now = time.time()

        if now - self.last_run < self.interval:
            return

        self.last_run = now

        strategies = self.registry.get_active_strategies()

        if not strategies:
            return

        scores = []

        for strat in strategies:

            metrics = strat.get_metrics()

            trades = metrics.get("sample_size", 0)

            if trades < self.min_trades:
                continue

            sharpe = metrics.get("sharpe", 0)
            pf = metrics.get("profit_factor", 0)
            win_rate = metrics.get("win_rate", 0)
            expectancy = metrics.get("expectancy", 0)

            score = (
                sharpe * 0.4
                + pf * 0.3
                + expectancy * 0.2
                + (win_rate / 100) * 0.1
            )

            scores.append((strat, score, sharpe))

        if not scores:
            return

        scores.sort(key=lambda x: x[1], reverse=True)

        self._reallocate(scores)

        self._retire(scores)

        self._promote(scores)

    def _reallocate(self, scores):

        total = sum(max(s[1], 0.01) for s in scores)

        allocations = {}

        for strat, score, _ in scores:

            weight = score / total

            allocations[strat.strategy_id] = weight * 100

        self.portfolio.update_allocations(allocations)

        print("AlphaCompetition: allocations updated", allocations)

    def _retire(self, scores):

        for strat, score, sharpe in scores:

            if sharpe < self.retirement_sharpe:

                print("AlphaCompetition: retiring", strat.strategy_id)

                self.registry.retire_strategy(strat.strategy_id)

    def _promote(self, scores):

        for strat, score, sharpe in scores:

            if sharpe > self.promotion_sharpe:

                if strat.stage != "LIVE":

                    print("AlphaCompetition: promoting", strat.strategy_id)

                    self.registry.promote_strategy(strat.strategy_id)