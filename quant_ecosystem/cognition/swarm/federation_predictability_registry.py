from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .predictability_signal import (
    PredictabilitySignal,
)


class FederationPredictabilityRegistry(
    AppendRegistry[
        PredictabilitySignal
    ]
):

    def signals(
        self,
    ) -> list[PredictabilitySignal]:

        return self.entries()