from typing import List

from .capacity_metric import (
    CapacityMetric,
)


class FederationCapacityRegistry:

    def __init__(self):
        self._metrics: List[
            CapacityMetric
        ] = []

    def register(
        self,
        metric: CapacityMetric,
    ) -> None:

        self._metrics.append(metric)

    def metrics(self):

        return list(self._metrics)

    def count(self) -> int:

        return len(self._metrics)