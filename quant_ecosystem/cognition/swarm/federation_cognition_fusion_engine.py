from .federation_cognition_snapshot import (
    FederationCognitionSnapshot,
)
from .federation_cognition_report import (
    FederationCognitionReport,
)


class FederationCognitionFusionEngine:

    def evaluate(
        self,
        snapshot: FederationCognitionSnapshot,
    ) -> FederationCognitionReport:

        dimensions = {
            "performance": snapshot.performance,
            "risk": snapshot.risk,
            "resilience": snapshot.resilience,
            "capacity": snapshot.capacity,
            "improvement": snapshot.improvement,
            "compliance": snapshot.compliance,
            "stability": snapshot.stability,
            "trust": snapshot.trust,
            "adaptation": snapshot.adaptation,
            "predictability": snapshot.predictability,
            "cohesion": snapshot.cohesion,
        }

        cognition_index = (
            sum(dimensions.values())
            / len(dimensions)
        )

        strongest = max(
            dimensions,
            key=dimensions.get,
        )

        weakest = min(
            dimensions,
            key=dimensions.get,
        )

        return FederationCognitionReport(
            cognition_index=cognition_index,
            strongest_dimension=strongest,
            weakest_dimension=weakest,
        )