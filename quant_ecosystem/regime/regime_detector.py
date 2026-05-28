from quant_ecosystem.regime.market_regime import (
    MarketRegime,
)


class RegimeDetector:

    def detect(
        self,
        *,
        volatility,
        liquidity,
        trend_strength,
    ):

        if volatility >= 0.9:
            return (
                MarketRegime.CRISIS
            )

        if volatility >= 0.7:
            return (
                MarketRegime.VOLATILE
            )

        if liquidity <= 0.2:
            return (
                MarketRegime
                .LOW_LIQUIDITY
            )

        if trend_strength >= 0.8:
            return (
                MarketRegime
                .TRENDING
            )

        return (
            MarketRegime.NORMAL
        )


regime_detector = (
    RegimeDetector()
)