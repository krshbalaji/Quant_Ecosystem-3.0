from .federation_cognition_action_plan import (
    FederationCognitionActionPlan,
)
from .federation_cognition_execution_report import (
    FederationCognitionExecutionReport,
)


class FederationCognitionExecutionCoordinator:

    def coordinate(
        self,
        plan: FederationCognitionActionPlan,
    ) -> FederationCognitionExecutionReport:

        workflow_mapping = {
            "EXECUTE_STABILIZATION_PLAN":
                "stability_workflow",
            "EXECUTE_IMPROVEMENT_PLAN":
                "improvement_workflow",
            "ACCELERATE_STRATEGIC_GROWTH":
                "growth_workflow",
            "MAINTAIN_CURRENT_STATE":
                "monitoring_workflow",
        }

        workflow = workflow_mapping.get(
            plan.action,
            "manual_review_workflow",
        )

        return FederationCognitionExecutionReport(
            workflow_name=workflow,
            action=plan.action,
            execution_ready=True,
        )