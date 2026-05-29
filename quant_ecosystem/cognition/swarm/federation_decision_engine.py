from .architecture_decision_report import (
    ArchitectureDecisionReport,
)
from .federation_decision_registry import (
    FederationDecisionRegistry,
)


class FederationDecisionEngine:

    def evaluate(
        self,
        registry: FederationDecisionRegistry,
    ) -> ArchitectureDecisionReport:

        if not registry.candidates():

            return (
                ArchitectureDecisionReport(
                    recommended_category="none",
                    priority_score=0.0,
                )
            )

        winner = max(
            registry.candidates(),
            key=lambda x: x.priority_score,
        )

        return ArchitectureDecisionReport(
            recommended_category=(
                winner.category_name
            ),
            priority_score=(
                winner.priority_score
            ),
        )