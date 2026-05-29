from .federation_capability_registry import (
    FederationCapabilityRegistry,
)
from .federation_health_report import (
    FederationHealthReport,
)


class FederationDiagnosticEngine:

    def evaluate(
        self,
        registry: FederationCapabilityRegistry,
    ) -> FederationHealthReport:

        total = registry.count()
        healthy = registry.active_count()

        return FederationHealthReport(
            total_capabilities=total,
            healthy_capabilities=healthy,
        )