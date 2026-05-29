from .federation_execution_governance_registry import (
    FederationExecutionGovernanceRegistry,
)
from .governance_decision import (
    GovernanceDecision,
)


class FederationExecutionGovernanceEngine:

    def evaluate(
        self,
        registry: (
            FederationExecutionGovernanceRegistry
        ),
    ):

        decisions = []

        for initiative in (
            registry.initiatives()
        ):
            decisions.append(
                GovernanceDecision(
                    initiative_id=(
                        initiative.initiative_id
                    ),
                    approved=(
                        initiative.approved
                    ),
                )
            )

        return decisions