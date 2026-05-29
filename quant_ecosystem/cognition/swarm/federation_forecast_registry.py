from typing import List

from .forecast_projection import (
    ForecastProjection,
)


class FederationForecastRegistry:

    def __init__(self):
        self._projections: List[
            ForecastProjection
        ] = []

    def register(
        self,
        projection: ForecastProjection,
    ) -> None:

        self._projections.append(
            projection
        )

    def projections(self):

        return list(
            self._projections
        )

    def count(self) -> int:

        return len(
            self._projections
        )