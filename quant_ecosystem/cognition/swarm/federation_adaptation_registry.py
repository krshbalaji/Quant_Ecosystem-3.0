from .adaptation_signal import (
    AdaptationSignal,
)


class FederationAdaptationRegistry:

    def __init__(self) -> None:
        self._signals: list[
            AdaptationSignal
        ] = []

    def register(
        self,
        signal: AdaptationSignal,
    ) -> None:
        self._signals.append(signal)

    def signals(
        self,
    ) -> list[AdaptationSignal]:
        return list(self._signals)