from .architecture_efficiency_report import (
    ArchitectureEfficiencyReport,
)
from .federation_efficiency_registry import (
    FederationEfficiencyRegistry,
)


class FederationEfficiencyEngine:

    def evaluate(
        self,
        registry: FederationEfficiencyRegistry,
    ) -> ArchitectureEfficiencyReport:

        metrics = registry.metrics()

        if not metrics:

            return (
                ArchitectureEfficiencyReport(
                    average_efficiency=0.0,
                    category_count=0,
                )
            )

        efficiencies = []

        for metric in metrics:

            if metric.total_components == 0:
                efficiencies.append(0.0)
            else:
                efficiencies.append(
                    metric.utilized_components
                    / metric.total_components
                )

        return ArchitectureEfficiencyReport(
            average_efficiency=(
                sum(efficiencies)
                / len(efficiencies)
            ),
            category_count=len(metrics),
        )