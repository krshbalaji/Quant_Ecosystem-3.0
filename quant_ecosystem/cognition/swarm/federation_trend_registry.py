from typing import List

from .architecture_trend_point import (
    ArchitectureTrendPoint,
)


class FederationTrendRegistry:

    def __init__(self):
        self._points: List[
            ArchitectureTrendPoint
        ] = []

    def register(
        self,
        point: ArchitectureTrendPoint,
    ) -> None:

        self._points.append(point)

    def points(self):

        return list(
            self._points
        )

    def count(self) -> int:

        return len(
            self._points
        )