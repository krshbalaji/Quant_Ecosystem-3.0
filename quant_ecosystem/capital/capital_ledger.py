class CapitalLedger:

    def __init__(self):

        self._strategy_capital = {}

        self._broker_capital = {}

        self._global_capital = 0.0

    def allocate(
        self,
        *,
        strategy,
        broker,
        capital,
    ):

        self._strategy_capital[
            strategy
        ] = (
            self._strategy_capital.get(
                strategy,
                0.0,
            )
            + capital
        )

        self._broker_capital[
            broker
        ] = (
            self._broker_capital.get(
                broker,
                0.0,
            )
            + capital
        )

        self._global_capital += capital

    def strategy_usage(
        self,
        strategy,
    ):
        return (
            self._strategy_capital.get(
                strategy,
                0.0,
            )
        )

    def broker_usage(
        self,
        broker,
    ):
        return (
            self._broker_capital.get(
                broker,
                0.0,
            )
        )

    @property
    def total_usage(self):
        return self._global_capital


capital_ledger = (
    CapitalLedger()
)