class StrategyRegistry:

    def __init__(self):
        self.strategies = []

    def register(self, strategy):
        self.strategies.append(strategy)

    def list(self):
        return self.strategies