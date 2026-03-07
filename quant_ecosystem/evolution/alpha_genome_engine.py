import random
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AlphaGenomeEngine:
    """
    Generates base strategy genomes that the system can evolve.

    Each genome describes a strategy configuration that later gets
    mutated, backtested, and evolved.
    """

    def __init__(self, **kwargs):
        logger.info("AlphaGenomeEngine initialized")

        self.indicators = [
            "sma",
            "ema",
            "rsi",
            "macd",
            "bollinger",
            "atr",
            "momentum"
        ]

        self.timeframes = ["5m", "15m", "1h", "4h", "1d"]

    def random_parameters(self, indicator: str):

        if indicator == "sma":
            return {"window": random.randint(5, 200)}

        if indicator == "ema":
            return {"window": random.randint(5, 200)}

        if indicator == "rsi":
            return {"period": random.randint(7, 21)}

        if indicator == "macd":
            return {
                "fast": random.randint(5, 12),
                "slow": random.randint(20, 40),
                "signal": random.randint(5, 15)
            }

        if indicator == "bollinger":
            return {
                "window": random.randint(10, 40),
                "std": random.uniform(1.5, 3)
            }

        if indicator == "atr":
            return {"period": random.randint(7, 21)}

        if indicator == "momentum":
            return {"period": random.randint(5, 30)}

        return {}

    def generate_genome(self) -> Dict:

        indicator = random.choice(self.indicators)

        genome = {

            "indicator": indicator,

            "parameters": self.random_parameters(indicator),

            "timeframe": random.choice(self.timeframes),

            "entry_rule": random.choice([
                "cross_above",
                "cross_below",
                "threshold_break",
                "momentum_spike"
            ]),

            "exit_rule": random.choice([
                "mean_reversion",
                "fixed_stop",
                "trailing_stop",
                "volatility_exit"
            ])

        }

        return genome

    def generate_population(self, size: int = 1000) -> List[Dict]:

        population = []

        for _ in range(size):
            population.append(self.generate_genome())

        logger.info(f"Generated {size} alpha genomes")

        return population