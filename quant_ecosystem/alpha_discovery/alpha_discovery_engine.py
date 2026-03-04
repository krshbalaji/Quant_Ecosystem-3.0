import random
import uuid
from datetime import datetime
from pathlib import Path
import json


class AlphaDiscoveryEngine:

    def __init__(self, strategy_lab_path="strategy_lab/research_strategies"):

        self.strategy_path = Path(strategy_lab_path)
        self.strategy_path.mkdir(parents=True, exist_ok=True)

        self.indicators = [
            "SMA",
            "EMA",
            "RSI",
            "MACD",
            "ATR",
            "BOLLINGER",
            "VWAP",
            "STOCH"
        ]

        self.entry_templates = [
            "momentum_breakout",
            "mean_reversion",
            "trend_following",
            "volatility_expansion",
            "volume_spike"
        ]

    def generate_strategy(self):

        indicator = random.choice(self.indicators)
        template = random.choice(self.entry_templates)

        strategy = {
            "id": f"alpha_{uuid.uuid4().hex[:8]}",
            "created": datetime.utcnow().isoformat(),
            "indicator": indicator,
            "template": template,
            "parameters": {
                "lookback": random.randint(5, 100),
                "threshold": round(random.uniform(0.5, 3.0), 2),
                "stop_loss": round(random.uniform(0.5, 3.0), 2),
                "take_profit": round(random.uniform(1.0, 5.0), 2)
            },
            "status": "discovered"
        }

        return strategy

    def save_strategy(self, strategy):

        filename = f"{strategy['id']}.json"
        path = self.strategy_path / filename

        with open(path, "w") as f:
            json.dump(strategy, f, indent=4)

        return path

    def discover(self, count=10):

        discovered = []

        for _ in range(count):

            strat = self.generate_strategy()
            path = self.save_strategy(strat)

            discovered.append(str(path))

        return discovered