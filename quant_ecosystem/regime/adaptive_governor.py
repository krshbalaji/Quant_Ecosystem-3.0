from quant_ecosystem.regime.market_regime import (
    MarketRegime,
)


class AdaptiveGovernor:

    def exposure_multiplier(
        self,
        regime,
    ):

        if regime == (
            MarketRegime.CRISIS
        ):
            return 0.25

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
            MarketRegime.RISK_OFF
        ):
            return 0.35

        return 1.0

    def retry_multiplier(
        self,
        regime,
    ):

        if regime == (
            MarketRegime.CRISIS
        ):
            return 0.25

        if regime == (
            MarketRegime.VOLATILE
        ):
            return 0.50

        return 1.0


adaptive_governor = (
    AdaptiveGovernor()
)