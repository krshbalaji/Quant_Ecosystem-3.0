"""Autonomous strategy template generator for the Strategy Lab."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, List, Optional


class StrategyGenerator:
    """Generates diverse strategy templates across multiple families."""

    STRATEGY_TYPES = [
        "trend_following",
        "mean_reversion",
        "breakout",
        "volatility",
        "pairs_trading",
        "momentum",
        "statistical_arbitrage",
    ]

    TIMEFRAMES = ["5m", "15m", "1h", "1d"]
    ASSET_CLASSES = ["stocks", "indices", "futures", "options", "forex", "crypto", "commodities"]
    INDICATORS = ["ema", "rsi", "atr", "bollinger", "vwap", "macd", "stochastic", "keltner", "aroon"]
    RISK_MODELS = ["fixed_risk", "atr_risk", "vol_target", "kelly_fractional"]

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def generate(self, count: int = 20) -> List[Dict]:
        """Generate `count` strategy templates."""
        out = []
        for _ in range(max(1, int(count))):
            stype = self._rng.choice(self.STRATEGY_TYPES)
            indicators = self._indicator_combo(stype)
            strategy_id = self._new_id(stype)
            out.append(
                {
                    "id": strategy_id,
                    "name": strategy_id,
                    "strategy_type": stype,
                    "category": stype,
                    "family": stype,
                    "asset_class": self._rng.choice(self.ASSET_CLASSES),
                    "timeframe": self._rng.choice(self.TIMEFRAMES),
                    "indicators": indicators,
                    "entry_logic": self._entry_logic(stype, indicators),
                    "exit_logic": self._exit_logic(stype),
                    "risk_model": self._rng.choice(self.RISK_MODELS),
                    "parameters": self._parameters(stype),
                    "stage": "RESEARCH",
                    "active": False,
                    "metadata": {
                        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "mutation_origin": "base_generator",
                    },
                }
            )
        return out

    def _new_id(self, strategy_type: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        return f"lab_{strategy_type}_{ts}"

    def _indicator_combo(self, strategy_type: str) -> List[str]:
        map_by_type = {
            "trend_following": ["ema", "atr", "vwap"],
            "momentum": ["ema", "rsi", "macd"],
            "mean_reversion": ["rsi", "bollinger", "stochastic"],
            "breakout": ["vwap", "atr", "keltner"],
            "volatility": ["atr", "bollinger", "keltner"],
            "pairs_trading": ["zscore", "ema", "atr"],
            "statistical_arbitrage": ["zscore", "bollinger", "vwap"],
        }
        pool = list(map_by_type.get(strategy_type, self.INDICATORS))
        if "zscore" not in self.INDICATORS and "zscore" in pool:
            self.INDICATORS.append("zscore")
        self._rng.shuffle(pool)
        return pool[:3]

    def _entry_logic(self, strategy_type: str, indicators: List[str]) -> str:
        if strategy_type in {"trend_following", "momentum"}:
            return "ema_fast_cross_ema_slow AND atr_filter"
        if strategy_type == "mean_reversion":
            return "rsi_oversold AND bollinger_lower_touch"
        if strategy_type == "breakout":
            return "vwap_breakout AND volume_spike"
        if strategy_type == "volatility":
            return "atr_expansion AND keltner_break"
        if strategy_type in {"pairs_trading", "statistical_arbitrage"}:
            return "zscore_extreme AND spread_reversion_signal"
        return f"{indicators[0]}_signal"

    def _exit_logic(self, strategy_type: str) -> str:
        if strategy_type in {"trend_following", "momentum"}:
            return "trailing_atr_stop OR ema_reversal"
        if strategy_type in {"mean_reversion", "pairs_trading", "statistical_arbitrage"}:
            return "mean_reversion_completed OR stop_loss"
        if strategy_type == "breakout":
            return "breakout_failure OR atr_stop"
        return "atr_stop OR time_exit"

    def _parameters(self, strategy_type: str) -> Dict:
        base = {
            "ema_fast": self._rng.randint(5, 15),
            "ema_slow": self._rng.randint(18, 55),
            "rsi_length": self._rng.randint(7, 21),
            "atr_length": self._rng.randint(7, 21),
            "atr_stop_mult": round(self._rng.uniform(1.2, 3.8), 4),
            "risk_multiple": round(self._rng.uniform(0.6, 2.5), 4),
            "volume_filter_mult": round(self._rng.uniform(1.0, 2.2), 4),
        }
        if strategy_type in {"pairs_trading", "statistical_arbitrage"}:
            base["zscore_entry"] = round(self._rng.uniform(1.5, 3.0), 4)
            base["zscore_exit"] = round(self._rng.uniform(0.1, 1.2), 4)
        return base

