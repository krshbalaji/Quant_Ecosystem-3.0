from .architecture_density_report import (
    ArchitectureDensityReport,
)
from .federation_density_registry import (
    FederationDensityRegistry,
)


class FederationDensityEngine:

    def evaluate(
        self,
        registry: FederationDensityRegistry,
    ) -> ArchitectureDensityReport:

        if not registry.metrics():

            return ArchitectureDensityReport(
                densest_category="none",
                component_count=0,
            )

        densest = max(
            registry.metrics(),
            key=lambda m: m.component_count,
        )

        return ArchitectureDensityReport(
            densest_category=(
                densest.category_name
            ),
            component_count=(
                densest.component_count
            ),
        )