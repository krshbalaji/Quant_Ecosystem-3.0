from .cohesion_signal import (
    CohesionSignal,
)


class FederationCohesionRegistry:

    def __init__(self) -> None:
        self._signals: list[
            CohesionSignal
        ] = []

    def register(
        self,
        signal: CohesionSignal,
    ) -> None:
        self._signals.append(signal)

    def signals(
        self,
    ) -> list[CohesionSignal]:
        return list(self._signals)