from quant_ecosystem.regime.market_regime import (
    MarketRegime,
)


class ExecutionPersonality:

    def aggression(
        self,
        regime,
    ):

        if regime == (
            MarketRegime.CRISIS
        ):
            return 0.20

        if regime == (
            MarketRegime.VOLATILE
        ):
            return 0.50

        if regime == (
            MarketRegime
            .LOW_LIQUIDITY
        ):
            return 0.40

        if regime == (
            MarketRegime.TRENDING
        ):
            return 1.25

        return 1.0


execution_personality = (
    ExecutionPersonality()
)