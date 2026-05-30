from .capacity_report import (
    CapacityReport,
)
from .federation_capacity_registry import (
    FederationCapacityRegistry,
)


class FederationCapacityEngine:

    def evaluate(
        self,
        registry: FederationCapacityRegistry,
    ) -> CapacityReport:

        metrics = registry.metrics()

        if not metrics:

            return CapacityReport(
                highest_utilization_category="none",
                utilization_ratio=0.0,
            )

        highest = max(
            metrics,
            key=lambda x:
                (
                    x.utilized_capacity
                    / x.total_capacity
                )
                if x.total_capacity > 0
                else 0.0,
        )

        ratio = (
            highest.utilized_capacity
            / highest.total_capacity
        ) if (
            highest.total_capacity > 0
        ) else 0.0

        return CapacityReport(
            highest_utilization_category=(
                highest.category_name
            ),
            utilization_ratio=ratio,
        )