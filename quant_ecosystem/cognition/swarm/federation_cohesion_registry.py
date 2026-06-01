from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .cohesion_signal import (
    CohesionSignal,
)


class FederationCohesionRegistry(
    AppendRegistry[
        CohesionSignal
    ]
):

    def signals(
        self,
    ) -> list[CohesionSignal]:

        return self.entries()