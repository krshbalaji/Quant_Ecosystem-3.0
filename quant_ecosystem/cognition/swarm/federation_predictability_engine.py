from .predictability_report import (
    PredictabilityReport,
)
from .federation_predictability_registry import (
    FederationPredictabilityRegistry,
)


class FederationPredictabilityEngine:

    def evaluate(
        self,
        registry: FederationPredictabilityRegistry,
    ) -> PredictabilityReport:

        signals = registry.signals()

        if not signals:
            return PredictabilityReport(
                federation_id="unknown",
                predictability_score=0.0,
                strongest_source="none",
                signal_count=0,
            )

        strongest = max(
            signals,
            key=lambda x: x.predictability_score,
        )

        avg_score = (
            sum(
                x.predictability_score
                for x in signals
            )
            / len(signals)
        )

        return PredictabilityReport(
            federation_id=strongest.federation_id,
            predictability_score=avg_score,
            strongest_source=strongest.source,
            signal_count=len(signals),
        )