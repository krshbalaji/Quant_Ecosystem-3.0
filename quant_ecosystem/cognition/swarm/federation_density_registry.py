from typing import List

from .architecture_density_metric import (
    ArchitectureDensityMetric,
)


class FederationDensityRegistry:

    def __init__(self):
        self._metrics: List[
            ArchitectureDensityMetric
        ] = []

    def register(
        self,
        metric: ArchitectureDensityMetric,
    ) -> None:

        self._metrics.append(metric)

    def metrics(self):

        return list(self._metrics)

    def count(self) -> int:

        return len(self._metrics)