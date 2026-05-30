from .trust_report import (
    TrustReport,
)
from .federation_trust_registry import (
    FederationTrustRegistry,
)


class FederationTrustEngine:

    def evaluate(
        self,
        registry: FederationTrustRegistry,
    ) -> TrustReport:

        metrics = registry.metrics()

        if not metrics:
            return TrustReport(
                federation_id="unknown",
                trust_score=0.0,
                strongest_source="none",
                metric_count=0,
            )

        strongest = max(
            metrics,
            key=lambda x: x.trust_score,
        )

        avg_score = (
            sum(
                x.trust_score
                for x in metrics
            )
            / len(metrics)
        )

        return TrustReport(
            federation_id=strongest.federation_id,
            trust_score=avg_score,
            strongest_source=strongest.source,
            metric_count=len(metrics),
        )