from .workflow_context import (
    WorkflowContext,
)
from .workflow_execution_summary import (
    WorkflowExecutionSummary,
)
from .workflow_integration_registry import (
    WorkflowIntegrationRegistry,
)


class FederationWorkflowIntegrator:

    def __init__(
        self,
        registry: WorkflowIntegrationRegistry,
    ):
        self.registry = registry

    def execute(
        self,
        context: WorkflowContext,
    ) -> WorkflowExecutionSummary:

        enabled = (
            self.registry.enabled_steps()
        )

        completed = len(enabled)

        context.values[
            "completed_steps"
        ] = completed

        return WorkflowExecutionSummary(
            total_steps=completed,
            completed_steps=completed,
            successful=True,
        )