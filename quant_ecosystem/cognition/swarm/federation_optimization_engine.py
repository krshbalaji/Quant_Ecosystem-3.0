from .architecture_optimization_report import (
    ArchitectureOptimizationReport,
)
from .federation_optimization_registry import (
    FederationOptimizationRegistry,
)


class FederationOptimizationEngine:

    def evaluate(
        self,
        registry: FederationOptimizationRegistry,
    ) -> ArchitectureOptimizationReport:

        if not registry.candidates():

            return (
                ArchitectureOptimizationReport(
                    target_category="none",
                    component_count=0,
                )
            )

        candidate = max(
            registry.candidates(),
            key=lambda c: c.component_count,
        )

        return ArchitectureOptimizationReport(
            target_category=(
                candidate.category_name
            ),
            component_count=(
                candidate.component_count
            ),
        )