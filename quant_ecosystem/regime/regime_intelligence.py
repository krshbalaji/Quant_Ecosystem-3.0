from quant_ecosystem.regime.regime_memory import (
    regime_memory,
)

from quant_ecosystem.regime.market_regime import (
    MarketRegime,
)


class RegimeIntelligence:

    def dominant_regime(self):

        snapshot = (
            regime_memory.latest()
        )

        if snapshot is None:

            return (
                MarketRegime.NORMAL
            )

        try:

            return MarketRegime(
                snapshot.detected_regime
            )

        except Exception:

            return (
                MarketRegime.NORMAL
            )


regime_intelligence = (
    RegimeIntelligence()
)