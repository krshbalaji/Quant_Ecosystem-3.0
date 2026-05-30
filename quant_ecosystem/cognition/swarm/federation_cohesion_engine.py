from .cohesion_report import (
    CohesionReport,
)
from .federation_cohesion_registry import (
    FederationCohesionRegistry,
)


class FederationCohesionEngine:

    def evaluate(
        self,
        registry: FederationCohesionRegistry,
    ) -> CohesionReport:

        signals = registry.signals()

        if not signals:
            return CohesionReport(
                federation_id="unknown",
                cohesion_score=0.0,
                strongest_source="none",
                signal_count=0,
            )

        strongest = max(
            signals,
            key=lambda x: x.cohesion_score,
        )

        average = (
            sum(
                x.cohesion_score
                for x in signals
            )
            / len(signals)
        )

        return CohesionReport(
            federation_id=strongest.federation_id,
            cohesion_score=average,
            strongest_source=strongest.source,
            signal_count=len(signals),
        )