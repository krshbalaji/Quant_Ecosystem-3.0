"""Bounded parameter mutation utilities."""

from __future__ import annotations

import random
from typing import Dict

from quant_ecosystem.strategy_bank.mutation.strategy_dna import StrategyDNA


class ParameterMutator:
    """Mutates parameters inside bounded ranges for robustness."""

    BOUNDS: Dict[str, tuple] = {
        "lookback": (5, 200),
        "rsi_period": (5, 40),
        "ema_fast": (3, 50),
        "ema_slow": (10, 200),
        "atr_multiplier": (0.8, 5.0),
        "risk_multiple": (0.5, 4.0),
    }

    INDICATOR_SWAP = {
        "macd": "aroon",
        "aroon": "macd",
        "rsi": "stochastic",
        "stochastic": "rsi",
        "bollinger": "keltner",
        "keltner": "bollinger",
        "ema_cross": "vwap_cross",
        "vwap_cross": "ema_cross",
    }

    TIMEFRAME_CHAIN = ["5m", "15m", "1h", "1d"]

    def mutate(self, dna: StrategyDNA) -> StrategyDNA:
        params = dict(dna.parameters)
        for key, value in list(params.items()):
            if random.random() > 0.5:
                continue
            bounds = self.BOUNDS.get(key)
            if bounds:
                low, high = bounds
                if isinstance(low, int) and isinstance(high, int):
                    params[key] = float(random.randint(low, high))
                else:
                    params[key] = round(random.uniform(float(low), float(high)), 4)
                continue
            span = max(0.1, abs(float(value)) * 0.25)
            params[key] = round(float(value) + random.uniform(-span, span), 4)

        if random.random() < 0.35:
            dna.stop_loss = round(max(0.1, dna.stop_loss + random.uniform(-0.3, 0.3)), 4)
        if random.random() < 0.35:
            dna.take_profit = round(max(0.1, dna.take_profit + random.uniform(-0.5, 0.5)), 4)

        return StrategyDNA(
            entry_logic=dna.entry_logic,
            exit_logic=dna.exit_logic,
            stop_loss=dna.stop_loss,
            take_profit=dna.take_profit,
            indicators=list(dna.indicators),
            parameters=params,
            timeframe=dna.timeframe,
            asset_class=dna.asset_class,
        )

    def swap_indicator(self, dna: StrategyDNA) -> StrategyDNA:
        universe = ["ema", "sma", "rsi", "stochastic", "macd", "aroon", "atr", "bollinger", "keltner"]
        indicators = list(dna.indicators)
        if indicators and random.random() < 0.7:
            idx = random.randrange(0, len(indicators))
            current = str(indicators[idx]).lower()
            indicators[idx] = self.INDICATOR_SWAP.get(current, random.choice(universe))
        elif random.random() < 0.7:
            indicators.append(random.choice(universe))
        indicators = sorted(set(indicators))
        return StrategyDNA(
            entry_logic=dna.entry_logic,
            exit_logic=dna.exit_logic,
            stop_loss=dna.stop_loss,
            take_profit=dna.take_profit,
            indicators=indicators,
            parameters=dict(dna.parameters),
            timeframe=dna.timeframe,
            asset_class=dna.asset_class,
        )

    def tweak_logic(self, dna: StrategyDNA) -> StrategyDNA:
        entry_variants = [
            "trend_follow_entry",
            "pullback_entry",
            "breakout_entry",
            "mean_revert_entry",
            "rsi_gt_65_entry",
            "vwap_cross_entry",
        ]
        exit_variants = ["fixed_exit", "trailing_exit", "volatility_exit", "time_exit"]
        entry_logic = dna.entry_logic
        exit_logic = dna.exit_logic
        if random.random() < 0.5:
            entry_logic = random.choice(entry_variants)
        if random.random() < 0.5:
            exit_logic = random.choice(exit_variants)
        return StrategyDNA(
            entry_logic=entry_logic,
            exit_logic=exit_logic,
            stop_loss=dna.stop_loss,
            take_profit=dna.take_profit,
            indicators=list(dna.indicators),
            parameters=dict(dna.parameters),
            timeframe=dna.timeframe,
            asset_class=dna.asset_class,
        )

    def mutate_timeframe(self, dna: StrategyDNA) -> StrategyDNA:
        tf = str(dna.timeframe).lower()
        if tf not in self.TIMEFRAME_CHAIN:
            tf = "5m"
        idx = self.TIMEFRAME_CHAIN.index(tf)
        move = random.choice([-1, 1])
        next_idx = min(max(0, idx + move), len(self.TIMEFRAME_CHAIN) - 1)
        return StrategyDNA(
            entry_logic=dna.entry_logic,
            exit_logic=dna.exit_logic,
            stop_loss=dna.stop_loss,
            take_profit=dna.take_profit,
            indicators=list(dna.indicators),
            parameters=dict(dna.parameters),
            timeframe=self.TIMEFRAME_CHAIN[next_idx],
            asset_class=dna.asset_class,
        )

    def mutate_risk_model(self, dna: StrategyDNA) -> StrategyDNA:
        params = dict(dna.parameters)
        params["risk_multiple"] = round(
            max(0.5, min(4.0, float(params.get("risk_multiple", 1.5)) + random.uniform(-0.4, 0.4))),
            4,
        )
        params["scale_in_steps"] = round(
            max(1.0, min(5.0, float(params.get("scale_in_steps", 2.0)) + random.choice([-1.0, 1.0]))),
            4,
        )
        return StrategyDNA(
            entry_logic=dna.entry_logic,
            exit_logic=dna.exit_logic,
            stop_loss=round(max(0.1, dna.stop_loss + random.uniform(-0.25, 0.25)), 4),
            take_profit=round(max(0.1, dna.take_profit + random.uniform(-0.35, 0.35)), 4),
            indicators=list(dna.indicators),
            parameters=params,
            timeframe=dna.timeframe,
            asset_class=dna.asset_class,
        )
