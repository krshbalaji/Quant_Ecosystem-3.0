from .federation_improvement_registry import (
    FederationImprovementRegistry,
)
from .improvement_recommendation import (
    ImprovementRecommendation,
)


class FederationImprovementEngine:

    def evaluate(
        self,
        registry: FederationImprovementRegistry,
    ) -> ImprovementRecommendation:

        if not registry.candidates():

            return (
                ImprovementRecommendation(
                    recommended_category="none",
                    improvement_score=0.0,
                )
            )

        candidate = max(
            registry.candidates(),
            key=lambda c: (
                c.improvement_score
            ),
        )

        return (
            ImprovementRecommendation(
                recommended_category=(
                    candidate.category_name
                ),
                improvement_score=(
                    candidate.improvement_score
                ),
            )
        )