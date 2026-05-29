from .architecture_decision_report import (
    ArchitectureDecisionReport,
)
from .execution_request_builder import (
    ExecutionRequestBuilder,
)
from .execution_result import (
    ExecutionResult,
)
from .federation_action import (
    FederationAction,
)
from .federation_orchestrator import (
    FederationOrchestrator,
)


class DecisionActionBridge:

    def execute(
        self,
        decision: ArchitectureDecisionReport,
        orchestrator: (
            FederationOrchestrator
        ),
    ) -> ExecutionResult:

        action = FederationAction(
            action_id="AUTO",
            action_type=(
                decision.recommended_category
            ),
            payload={
                "priority_score": (
                    decision.priority_score
                )
            },
        )

        request = (
            ExecutionRequestBuilder()
            .build(action)
        )

        result = (
            orchestrator.execute(
                request
            )
        )

        return ExecutionResult(
            category_name=(
                decision.recommended_category
            ),
            successful=(
                result.successful
            ),
            stages_completed=(
                result.stages_completed
            ),
        )