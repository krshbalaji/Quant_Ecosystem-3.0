from .federation_performance_registry import (
    FederationPerformanceRegistry,
)
from .performance_report import (
    PerformanceReport,
)


class FederationPerformanceEngine:

    def evaluate(
        self,
        registry: (
            FederationPerformanceRegistry
        ),
    ) -> PerformanceReport:

        snapshots = (
            registry.snapshots()
        )

        if not snapshots:

            return PerformanceReport(
                total_executions=0,
                successful_executions=0,
                success_rate=0.0,
            )

        successful = sum(
            1
            for item in snapshots
            if item.successful
        )

        return PerformanceReport(
            total_executions=len(
                snapshots
            ),
            successful_executions=(
                successful
            ),
            success_rate=(
                successful
                / len(snapshots)
            ),
        )