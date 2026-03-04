class StrategyRegistry:

    def __init__(self):
        self._strategies = {}

    def register(self, strategy):
        self._strategies[strategy["id"]] = strategy

    def get(self, strategy_id):
        return self._strategies.get(strategy_id)

    def get_all(self):
        return list(self._strategies.values())

    def count(self):
        return len(self._strategies)