from .federation_resilience_registry import (
    FederationResilienceRegistry,
)
from .resilience_report import (
    ResilienceReport,
)


class FederationResilienceEngine:

    def evaluate(
        self,
        registry: FederationResilienceRegistry,
    ) -> ResilienceReport:

        indicators = (
            registry.indicators()
        )

        if not indicators:

            return ResilienceReport(
                strongest_category="none",
                resilience_score=0.0,
            )

        strongest = max(
            indicators,
            key=lambda x: (
                x.resilience_score
            ),
        )

        return ResilienceReport(
            strongest_category=(
                strongest.category_name
            ),
            resilience_score=(
                strongest.resilience_score
            ),
        )