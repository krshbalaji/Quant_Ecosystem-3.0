"""
Alpha Competition Engine
Institutional Alpha Tournament System

Purpose
-------
Continuously evaluate strategies and allow them to compete
for capital allocation.

Weak strategies lose allocation.
Strong strategies gain allocation.

This mimics how institutional hedge funds rotate alpha.
"""

from datetime import datetime


class AlphaCompetitionEngine:

    def __init__(self, strategy_registry, portfolio_engine=None):

        self.registry = strategy_registry
        self.portfolio = portfolio_engine

        self.last_competition = None
        self.competition_interval = 60  # seconds

    def run_competition(self):

        strategies = self.registry.get_all()

        if not strategies:
            return

        ranked = []

        for strategy in strategies:

            metrics = strategy.get("metrics", {})

            score = self._compute_score(metrics)

            ranked.append((score, strategy))

        ranked.sort(reverse=True, key=lambda x: x[0])

        winners = ranked[:3]

        self.last_competition = datetime.utcnow()

        return winners

    def _compute_score(self, metrics):

        sharpe = metrics.get("sharpe", 0)
        win_rate = metrics.get("win_rate", 0)
        profit_factor = metrics.get("profit_factor", 0)
        drawdown = metrics.get("max_dd", 0)

        score = (
            sharpe * 2
            + win_rate * 0.02
            + profit_factor
            - drawdown * 0.1
        )

        return score

    def allocate_capital(self):

        winners = self.run_competition()

        if not winners or not self.portfolio:
            return

        allocation = {}

        capital_weights = [0.5, 0.3, 0.2]

        for i, (_, strategy) in enumerate(winners):

            sid = strategy["id"]

            allocation[sid] = capital_weights[i]

        self.portfolio.apply_allocation(allocation)

        return allocation