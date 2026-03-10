import random
import logging

logger = logging.getLogger(__name__)


class PortfolioEvolutionEngine:

    def __init__(self, strategy_bank):

        self.strategy_bank = strategy_bank

    def generate_portfolio(self):

        strategies = self.strategy_bank.get_strategies()

        if not strategies:
            return None

        selected = random.sample(
            strategies,
            min(len(strategies), random.randint(3, 6))
        )

        weights = self._random_weights(len(selected))

        portfolio = []

        for strat, w in zip(selected, weights):

            portfolio.append({
                "strategy": strat,
                "weight": w
            })

        return portfolio

    def mutate_portfolio(self, portfolio):

        if not portfolio:
            return portfolio

        i = random.randint(0, len(portfolio) - 1)

        portfolio[i]["weight"] *= random.uniform(0.7, 1.3)

        return portfolio

    def _random_weights(self, n):

        vals = [random.random() for _ in range(n)]

        s = sum(vals)

        return [v / s for v in vals]