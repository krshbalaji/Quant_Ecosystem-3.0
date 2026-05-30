from .stability_report import (
    StabilityReport,
)
from .federation_stability_registry import (
    FederationStabilityRegistry,
)


class FederationStabilityEngine:

    def evaluate(
        self,
        registry: FederationStabilityRegistry,
    ) -> StabilityReport:

        indicators = registry.indicators()

        if not indicators:
            return StabilityReport(
                federation_id="unknown",
                stability_score=0.0,
                strongest_source="none",
                indicator_count=0,
            )

        strongest = max(
            indicators,
            key=lambda x: x.stability_score,
        )

        avg_score = (
            sum(
                x.stability_score
                for x in indicators
            )
            / len(indicators)
        )

        return StabilityReport(
            federation_id=strongest.federation_id,
            stability_score=avg_score,
            strongest_source=strongest.source,
            indicator_count=len(indicators),
        )