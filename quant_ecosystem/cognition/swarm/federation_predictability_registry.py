from .predictability_signal import (
    PredictabilitySignal,
)


class FederationPredictabilityRegistry:

    def __init__(self) -> None:
        self._signals: list[
            PredictabilitySignal
        ] = []

    def register(
        self,
        signal: PredictabilitySignal,
    ) -> None:
        self._signals.append(signal)

    def signals(
        self,
    ) -> list[PredictabilitySignal]:
        return list(self._signals)