from quant_ecosystem.capital.capital_ledger import (
    capital_ledger,
)


class CapitalGovernor:

    MAX_GLOBAL_CAPITAL = (
        100_000_000
    )

    MAX_STRATEGY_CAPITAL = (
        25_000_000
    )

    MAX_BROKER_CAPITAL = (
        50_000_000
    )

    def validate(
        self,
        *,
        strategy,
        broker,
        capital,
    ):

        projected_global = (
            capital_ledger.total_usage
            + capital
        )

        if (
            projected_global
            > self.MAX_GLOBAL_CAPITAL
        ):
            raise RuntimeError(
                "GLOBAL CAPITAL LIMIT"
            )

        projected_strategy = (
            capital_ledger
            .strategy_usage(strategy)
            + capital
        )

        if (
            projected_strategy
            > self.MAX_STRATEGY_CAPITAL
        ):
            raise RuntimeError(
                "STRATEGY CAPITAL LIMIT"
            )

        projected_broker = (
            capital_ledger
            .broker_usage(broker)
            + capital
        )

        if (
            projected_broker
            > self.MAX_BROKER_CAPITAL
        ):
            raise RuntimeError(
                "BROKER CAPITAL LIMIT"
            )

    def register(
        self,
        *,
        strategy,
        broker,
        capital,
    ):

        capital_ledger.allocate(
            strategy=strategy,
            broker=broker,
            capital=capital,
        )


capital_governor = (
    CapitalGovernor()
)