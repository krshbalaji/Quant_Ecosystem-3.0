from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .adaptation_signal import (
    AdaptationSignal,
)


class FederationAdaptationRegistry(
    AppendRegistry[
        AdaptationSignal
    ]
):

    def signals(
        self,
    ) -> list[AdaptationSignal]:

        return self.entries()