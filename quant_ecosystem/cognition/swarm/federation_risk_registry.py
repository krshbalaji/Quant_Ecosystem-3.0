from typing import List

from .risk_indicator import (
    RiskIndicator,
)


class FederationRiskRegistry:

    def __init__(self):
        self._indicators: List[
            RiskIndicator
        ] = []

    def register(
        self,
        indicator: RiskIndicator,
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