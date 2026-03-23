class PromotionProbabilityEngine:

    def __init__(self):

        self.base_threshold = -0.50

    def compute_probability(self, result):

        fitness = result.fitness
        sharpe = result.sharpe
        trades = result.total_trades

        prob = 0.5

        if fitness > 0:
            prob += 0.25

        if sharpe > 1:
            prob += 0.20

        if trades > 40:
            prob += 0.15

        return min(prob, 0.95)

    def should_promote(self, result):

        import random

        p = self.compute_probability(result)

        return random.random() < p