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
import logging
from datetime import datetime

logger = logging.getLogger("AlphaCompetitionEngine")


class AlphaCompetitionEngine:
    """
    Strategy tournament engine.

    Periodically evaluates all strategies in the registry and ranks them
    based on performance metrics.

    The best strategies receive capital allocation priority.
    Weak strategies are demoted or disabled.
    """

    def __init__(self, strategy_registry):
        self.strategy_registry = strategy_registry
        self.last_results = []

    # ---------------------------------------------------------
    # Public API expected by MasterOrchestrator
    # ---------------------------------------------------------

    def evaluate(self):

        # ------------------------------------------------
        # Get strategies safely from registry
        # ------------------------------------------------

        if hasattr(self.strategy_registry, "get_all"):
            strategies = self.strategy_registry.get_all()

        elif hasattr(self.strategy_registry, "get_strategies"):
            strategies = self.strategy_registry.get_strategies()

        elif hasattr(self.strategy_registry, "all"):
            strategies = self.strategy_registry.all()

        elif hasattr(self.strategy_registry, "strategies"):
            strategies = list(self.strategy_registry.strategies.values())

        else:
            logger.warning("AlphaCompetition: No strategy retrieval method found.")
            return []

        if not strategies:
            logger.info("AlphaCompetition: No strategies registered.")
            return []

        results = []

        for strategy in strategies:

            metrics = getattr(strategy, "metrics", None)

            if not metrics:
                continue

            score = self._score(metrics)

            results.append({
                "id": getattr(strategy, "id", "unknown"),
                "score": score,
                "metrics": metrics
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        self.last_results = results

        self._apply_rankings(results)

        logger.info(f"AlphaCompetition: ranked {len(results)} strategies")

        return results

    # ---------------------------------------------------------
    # Scoring Model
    # ---------------------------------------------------------

    def _score(self, metrics):
        """
        Convert metrics into a competition score.
        """

        win_rate = metrics.get("win_rate", 0)
        sharpe = metrics.get("sharpe", 0)
        profit_factor = metrics.get("profit_factor", 0)
        max_dd = metrics.get("max_dd", 0)

        score = (
            win_rate * 0.3 +
            sharpe * 0.4 +
            profit_factor * 0.2 -
            max_dd * 0.1
        )

        return score

    # ---------------------------------------------------------
    # Ranking Application
    # ---------------------------------------------------------

    def _apply_rankings(self, rankings):

        if not rankings:
            return

        top_cut = max(1, int(len(rankings) * 0.2))

        winners = rankings[:top_cut]

        for entry in winners:

            strategy = self.strategy_registry.get(entry["id"])

            if strategy:
                strategy.active = True
                strategy.priority = "HIGH"

        for entry in rankings[top_cut:]:

            strategy = self.strategy_registry.get(entry["id"])

            if strategy:
                strategy.priority = "LOW"




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

    if hasattr(self.system, "capital_intelligence"):
        self.system.capital_intelligence.evaluate()
    
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