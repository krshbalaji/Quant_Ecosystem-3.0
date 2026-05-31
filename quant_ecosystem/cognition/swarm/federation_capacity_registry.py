from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .capacity_metric import (
    CapacityMetric,
)


class FederationCapacityRegistry(
    AppendRegistry[
        CapacityMetric
    ]
):

    def metrics(
        self,
    ) -> list[CapacityMetric]:

        return self.entries()