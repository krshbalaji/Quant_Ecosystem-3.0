from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .stability_indicator import (
    StabilityIndicator,
)


class FederationStabilityRegistry(
    AppendRegistry[
        StabilityIndicator
    ]
):

    def indicators(
        self,
    ) -> list[StabilityIndicator]:

        return self.entries()