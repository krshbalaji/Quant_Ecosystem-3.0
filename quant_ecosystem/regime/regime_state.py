from quant_ecosystem.regime.market_regime import (
    MarketRegime,
)


class RegimeState:

    def __init__(self):

        self._current = (
            MarketRegime.NORMAL
        )

    def set(
        self,
        regime,
    ):

        self._current = regime

    def current(self):

        return self._current


regime_state = (
    RegimeState()
)