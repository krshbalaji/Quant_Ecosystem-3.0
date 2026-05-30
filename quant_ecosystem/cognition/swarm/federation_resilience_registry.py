from typing import List

from .resilience_indicator import (
    ResilienceIndicator,
)


class FederationResilienceRegistry:

    def __init__(self):
        self._indicators: List[
            ResilienceIndicator
        ] = []

    def register(
        self,
        indicator: ResilienceIndicator,
    ) -> None:

        self._indicators.append(
            indicator
        )

    def indicators(self):

        return list(
            self._indicators
        )

    def count(self) -> int:

        return len(
            self._indicators
        )