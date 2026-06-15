from .workflow_definition import (
    WorkflowDefinition,
)

from quant_ecosystem.core.registry_threading import (
    ThreadSafeRegistry,
)


class WorkflowRegistry(
    ThreadSafeRegistry[
        str,
        WorkflowDefinition,
    ]
):

    def register(
        self,
        key: str,
        value: WorkflowDefinition,
    ) -> None:
        super().register(key, value)

    def get(
        self,
        key: str,
    ) -> WorkflowDefinition:
        return super().get(key)

    def register_workflow(
        self,
        workflow: WorkflowDefinition,
    ) -> None:

        if self.exists(workflow.workflow_id):
            return

        self.register(
            workflow.workflow_id,
            workflow,
        )

    def get_workflow(
        self,
        workflow_id: str,
    ) -> WorkflowDefinition | None:

        if not self.exists(workflow_id):
            return None

        return super().get(
            workflow_id,
        )