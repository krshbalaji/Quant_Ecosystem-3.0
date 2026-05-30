from .trust_metric import (
    TrustMetric,
)


class FederationTrustRegistry:

    def __init__(self) -> None:
        self._metrics: list[
            TrustMetric
        ] = []

    def register(
        self,
        metric: TrustMetric,
    ) -> None:
        self._metrics.append(metric)

    def metrics(
        self,
    ) -> list[TrustMetric]:
        return list(self._metrics)