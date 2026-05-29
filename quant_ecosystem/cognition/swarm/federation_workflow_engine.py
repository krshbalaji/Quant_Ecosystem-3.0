from .workflow_definition import (
    WorkflowDefinition,
)
from .workflow_execution_record import (
    WorkflowExecutionRecord,
)
from .workflow_stage_result import (
    WorkflowStageResult,
)


class FederationWorkflowEngine:

    def execute(
        self,
        workflow: WorkflowDefinition,
    ) -> WorkflowExecutionRecord:

        results = []

        for stage in workflow.stages:

            results.append(
                WorkflowStageResult(
                    stage_name=stage,
                    successful=True,
                )
            )

        return WorkflowExecutionRecord(
            workflow_id=workflow.workflow_id,
            successful=True,
            stage_results=results,
        )