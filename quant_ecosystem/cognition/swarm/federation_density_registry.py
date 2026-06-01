from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .architecture_density_metric import (
    ArchitectureDensityMetric,
)


class FederationDensityRegistry(
    AppendRegistry[
        ArchitectureDensityMetric
    ]
):

    def metrics(
        self,
    ) -> list[
        ArchitectureDensityMetric
    ]:

        return self.entries()