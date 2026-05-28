class ExposureRegistry:

    def __init__(self):

        self._symbol_exposure = {}

        self._broker_exposure = {}

        self._strategy_exposure = {}

    def update(
        self,
        *,
        symbol,
        broker,
        strategy,
        exposure,
    ):

        self._symbol_exposure[
            symbol
        ] = (
            self._symbol_exposure.get(
                symbol,
                0.0,
            )
            + exposure
        )

        self._broker_exposure[
            broker
        ] = (
            self._broker_exposure.get(
                broker,
                0.0,
            )
            + exposure
        )

        self._strategy_exposure[
            strategy
        ] = (
            self._strategy_exposure.get(
                strategy,
                0.0,
            )
            + exposure
        )

    def symbol_exposure(
        self,
        symbol,
    ):
        return (
            self._symbol_exposure.get(
                symbol,
                0.0,
            )
        )

    def broker_exposure(
        self,
        broker,
    ):
        return (
            self._broker_exposure.get(
                broker,
                0.0,
            )
        )

    def strategy_exposure(
        self,
        strategy,
    ):
        return (
            self._strategy_exposure.get(
                strategy,
                0.0,
            )
        )


exposure_registry = (
    ExposureRegistry()
)