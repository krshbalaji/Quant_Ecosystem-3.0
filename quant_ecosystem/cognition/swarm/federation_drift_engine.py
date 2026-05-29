from .architecture_drift_report import (
    ArchitectureDriftReport,
)
from .federation_drift_registry import (
    FederationDriftRegistry,
)


class FederationDriftEngine:

    def evaluate(
        self,
        registry: FederationDriftRegistry,
    ) -> ArchitectureDriftReport:

        snapshots = (
            registry.snapshots()
        )

        if len(snapshots) < 2:

            return (
                ArchitectureDriftReport(
                    component_growth=0,
                    growth_detected=False,
                )
            )

        growth = (
            snapshots[-1].component_count
            - snapshots[0].component_count
        )

        return ArchitectureDriftReport(
            component_growth=growth,
            growth_detected=(
                growth > 0
            ),
        )