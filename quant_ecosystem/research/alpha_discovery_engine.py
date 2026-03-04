import random
import uuid


class AlphaDiscoveryEngine:

    def __init__(self, strategy_registry):
        self.strategy_registry = strategy_registry

    def generate_strategy(self):

        indicators = [
            "RSI",
            "MACD",
            "EMA",
            "BOLLINGER",
            "VWAP"
        ]

        entry_indicator = random.choice(indicators)
        exit_indicator = random.choice(indicators)

        strategy = {
            "id": str(uuid.uuid4()),
            "name": f"alpha_{entry_indicator}_{exit_indicator}",
            "entry": entry_indicator,
            "exit": exit_indicator,
            "parameters": {
                "lookback": random.randint(5, 50),
                "threshold": random.uniform(0.5, 2.5)
            }
        }

        return strategy

    def discover(self, count=5):

        discovered = []

        for _ in range(count):

            strategy = self.generate_strategy()

            self.strategy_registry.register(strategy)

            discovered.append(strategy)

        return discovered

    # Unified interface helper
    def run(self, count=5):
        """
        Generic entry point expected by orchestration layers.
        """
        return self.discover(count=count)