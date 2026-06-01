from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .resilience_indicator import (
    ResilienceIndicator,
)


class FederationResilienceRegistry(
    AppendRegistry[
        ResilienceIndicator
    ]
):

    def indicators(
        self,
    ) -> list[ResilienceIndicator]:

        return self.entries()