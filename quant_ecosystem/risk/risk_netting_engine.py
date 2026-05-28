from quant_ecosystem.risk.exposure_registry import (
    exposure_registry,
)


class RiskNettingEngine:

    MAX_SYMBOL_EXPOSURE = 5_000_000

    MAX_BROKER_EXPOSURE = 25_000_000

    MAX_STRATEGY_EXPOSURE = 10_000_000

    def validate(
        self,
        *,
        symbol,
        broker,
        strategy,
        exposure,
    ):

        projected_symbol = (
            exposure_registry
            .symbol_exposure(symbol)
            + exposure
        )

        if (
            projected_symbol
            > self.MAX_SYMBOL_EXPOSURE
        ):
            raise RuntimeError(
                "SYMBOL EXPOSURE LIMIT"
            )

        projected_broker = (
            exposure_registry
            .broker_exposure(broker)
            + exposure
        )

        if (
            projected_broker
            > self.MAX_BROKER_EXPOSURE
        ):
            raise RuntimeError(
                "BROKER EXPOSURE LIMIT"
            )

        projected_strategy = (
            exposure_registry
            .strategy_exposure(strategy)
            + exposure
        )

        if (
            projected_strategy
            > self.MAX_STRATEGY_EXPOSURE
        ):
            raise RuntimeError(
                "STRATEGY EXPOSURE LIMIT"
            )

    def register(
        self,
        *,
        symbol,
        broker,
        strategy,
        exposure,
    ):

        exposure_registry.update(
            symbol=symbol,
            broker=broker,
            strategy=strategy,
            exposure=exposure,
        )


risk_netting_engine = (
    RiskNettingEngine()
)