from quant_ecosystem.risk.correlation_registry import (
    correlation_registry,
)


class CorrelationRiskEngine:

    MAX_GROUP_EXPOSURE = (
        15_000_000
    )

    def __init__(self):

        self._group_exposure = {}

    def validate(
        self,
        *,
        symbol,
        exposure,
    ):

        group = (
            correlation_registry
            .group_for(symbol)
        )

        projected = (
            self._group_exposure.get(
                group,
                0.0,
            )
            + exposure
        )

        if (
            projected
            > self.MAX_GROUP_EXPOSURE
        ):
            raise RuntimeError(
                f"CORRELATION LIMIT: {group}"
            )

    def register(
        self,
        *,
        symbol,
        exposure,
    ):

        group = (
            correlation_registry
            .group_for(symbol)
        )

        self._group_exposure[
            group
        ] = (
            self._group_exposure.get(
                group,
                0.0,
            )
            + exposure
        )


correlation_risk_engine = (
    CorrelationRiskEngine()
)