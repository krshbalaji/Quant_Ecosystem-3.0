from .adaptation_report import (
    AdaptationReport,
)
from .federation_adaptation_registry import (
    FederationAdaptationRegistry,
)


class FederationAdaptationEngine:

    def evaluate(
        self,
        registry: FederationAdaptationRegistry,
    ) -> AdaptationReport:

        signals = registry.signals()

        if not signals:
            return AdaptationReport(
                federation_id="unknown",
                adaptation_score=0.0,
                strongest_source="none",
                signal_count=0,
            )

        strongest = max(
            signals,
            key=lambda x: x.adaptation_score,
        )

        avg_score = (
            sum(
                x.adaptation_score
                for x in signals
            )
            / len(signals)
        )

        return AdaptationReport(
            federation_id=strongest.federation_id,
            adaptation_score=avg_score,
            strongest_source=strongest.source,
            signal_count=len(signals),
        )