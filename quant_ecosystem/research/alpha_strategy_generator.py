import random
import uuid


class AlphaStrategyGenerator:

    def __init__(self, factor_engine, **kwargs):

        self.factor_engine = factor_engine

        self.factors = [
            "momentum",
            "rsi",
            "zscore",
            "volatility",
            "bollinger_pos",
            "volume_spike"
        ]

    def generate_strategy(self):

        f1 = random.choice(self.factors)
        f2 = random.choice(self.factors)

        threshold1 = random.uniform(-1, 1)
        threshold2 = random.uniform(-1, 1)

        strategy = {
            "id": str(uuid.uuid4()),
            "entry": [
                (f1, ">", threshold1),
                (f2, "<", threshold2)
            ],
            "exit": [
                (f1, "<", 0)
            ]
        }

        return strategy

    def generate_batch(self, n=1000):

        strategies = []

        for _ in range(n):

            strategies.append(self.generate_strategy())

        return strategies