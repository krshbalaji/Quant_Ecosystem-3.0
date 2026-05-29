from .federation_lifecycle_tracker import (
    FederationLifecycleTracker,
)
from .initiative_lifecycle_report import (
    InitiativeLifecycleReport,
)


class FederationLifecycleEngine:

    def evaluate(
        self,
        tracker: FederationLifecycleTracker,
    ) -> InitiativeLifecycleReport:

        return InitiativeLifecycleReport(
            total_records=tracker.count(),
            active_records=(
                tracker.active_count()
            ),
        )