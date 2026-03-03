"""DNA crossover engine for synthetic strategy generation."""

from __future__ import annotations

import random

from strategy_bank.mutation.strategy_dna import StrategyDNA


class CrossoverEngine:
    """Combines two parent DNAs into one child DNA."""

    def crossover(self, left: StrategyDNA, right: StrategyDNA) -> StrategyDNA:
        parameters = dict(left.parameters)
        for key, value in right.parameters.items():
            if random.random() < 0.5:
                parameters[key] = value

        indicators = sorted(set(left.indicators + right.indicators))
        if indicators and random.random() < 0.4:
            indicators = indicators[: max(1, len(indicators) // 2)]

        return StrategyDNA(
            entry_logic=left.entry_logic if random.random() < 0.5 else right.entry_logic,
            exit_logic=left.exit_logic if random.random() < 0.5 else right.exit_logic,
            stop_loss=round((left.stop_loss + right.stop_loss) / 2.0, 4),
            take_profit=round((left.take_profit + right.take_profit) / 2.0, 4),
            indicators=indicators,
            parameters=parameters,
            timeframe=left.timeframe if random.random() < 0.5 else right.timeframe,
            asset_class=left.asset_class if random.random() < 0.5 else right.asset_class,
        )
