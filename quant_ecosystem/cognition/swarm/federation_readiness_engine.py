from .federation_readiness_registry import (
    FederationReadinessRegistry,
)
from .readiness_report import (
    ReadinessReport,
)


class FederationReadinessEngine:

    def evaluate(
        self,
        registry: FederationReadinessRegistry,
    ) -> ReadinessReport:

        total = registry.count()

        if total == 0:
            score = 0.0
        else:
            score = (
                registry.ready_count()
                / total
            )

        return ReadinessReport(
            operationally_ready=(
                score >= 0.80
            ),
            readiness_score=score,
        )