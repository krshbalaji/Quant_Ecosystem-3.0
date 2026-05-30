from .stability_indicator import (
    StabilityIndicator,
)


class FederationStabilityRegistry:

    def __init__(self) -> None:
        self._indicators: list[
            StabilityIndicator
        ] = []

    def register(
        self,
        indicator: StabilityIndicator,
    ) -> None:
        self._indicators.append(indicator)

    def indicators(
        self,
    ) -> list[StabilityIndicator]:
        return list(self._indicators)