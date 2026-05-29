from typing import List

from .architecture_efficiency_metric import (
    ArchitectureEfficiencyMetric,
)


class FederationEfficiencyRegistry:

    def __init__(self):
        self._metrics: List[
            ArchitectureEfficiencyMetric
        ] = []

    def register(
        self,
        metric: ArchitectureEfficiencyMetric,
    ) -> None:

        self._metrics.append(metric)

    def metrics(self):

        return list(self._metrics)

    def count(self) -> int:

        return len(self._metrics)