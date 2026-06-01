from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .risk_indicator import (
    RiskIndicator,
)


class FederationRiskRegistry(
    AppendRegistry[
        RiskIndicator
    ]
):

    def indicators(
        self,
    ) -> list[RiskIndicator]:

        return self.entries()