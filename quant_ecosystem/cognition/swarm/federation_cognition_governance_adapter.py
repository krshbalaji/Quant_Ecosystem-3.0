from .federation_cognition_workflow_result import (
    FederationCognitionWorkflowResult,
)
from .federation_cognition_governance_report import (
    FederationCognitionGovernanceReport,
)


class FederationCognitionGovernanceAdapter:

    def adapt(
        self,
        workflow_result: FederationCognitionWorkflowResult,
    ) -> FederationCognitionGovernanceReport:

        if workflow_result.accepted:
            return FederationCognitionGovernanceReport(
                governance_action=(
                    "AUTHORIZE_EXECUTION_REVIEW"
                ),
                review_required=True,
            )

        return FederationCognitionGovernanceReport(
            governance_action=(
                "ESCALATE_GOVERNANCE_REVIEW"
            ),
            review_required=True,
        )