from .federation_cognition_execution_report import (
    FederationCognitionExecutionReport,
)
from .federation_cognition_workflow_result import (
    FederationCognitionWorkflowResult,
)


class FederationCognitionWorkflowAdapter:

    def adapt(
        self,
        report: FederationCognitionExecutionReport,
    ) -> FederationCognitionWorkflowResult:

        return FederationCognitionWorkflowResult(
            workflow_name=report.workflow_name,
            accepted=report.execution_ready,
        )