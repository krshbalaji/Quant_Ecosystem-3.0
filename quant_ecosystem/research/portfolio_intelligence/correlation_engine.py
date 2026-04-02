import random
from collections import defaultdict


class CorrelationEngine:

    def __init__(self):
        self.corr_matrix = defaultdict(lambda: defaultdict(float))

    def estimate(self, g1, g2):
        key = (g1.family, g2.family)

        base = self.corr_matrix[key]

        noise = random.uniform(-0.1, 0.1)

        return max(-1, min(1, base + noise))

    def update_learning(self, g1, g2, realised_corr):
        key = (g1.family, g2.family)

        self.corr_matrix[key] = (
            0.8 * self.corr_matrix[key] + 0.2 * realised_corr
        )