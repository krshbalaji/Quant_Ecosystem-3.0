import random
import uuid

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy


class StrategyDiscoveryEngine:

    def __init__(self, feature_engine, strategy_registry):

        self.feature_engine = feature_engine
        self.registry = strategy_registry

        self.max_new_strategies = 20

    # -------------------------------------------------

    def generate(self):

        new_strategies = []

        for _ in range(self.max_new_strategies):

            strategy = self._generate_strategy()

            if strategy:
                self.registry.register(strategy)
                new_strategies.append(strategy)

        return new_strategies

    # -------------------------------------------------

    def _generate_strategy(self):

        feature = random.choice([
            "rsi",
            "momentum",
            "volatility",
            "atr",
            "vwap"
        ])

        threshold = random.uniform(20, 80)

        strategy_id = f"generated_{uuid.uuid4().hex[:8]}"

        return GeneratedStrategy(
            strategy_id,
            feature,
            threshold
        )