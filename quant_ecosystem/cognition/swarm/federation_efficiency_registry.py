from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_efficiency_metric import (
    ArchitectureEfficiencyMetric,
)


class FederationEfficiencyRegistry(
    AppendRegistry[
        ArchitectureEfficiencyMetric
    ]
):

    def metrics(
        self,
    ) -> list[
        ArchitectureEfficiencyMetric
    ]:

        return self.entries()