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
        workflow: WorkflowDefinition,
    ) -> None:

        if self.exists(
            workflow.workflow_id
        ):
            return

        super().register(
            workflow.workflow_id,
            workflow,
        )

    def get(
        self,
        workflow_id: str,
    ):

        if not self.exists(
            workflow_id
        ):
            return None

        return super().get(
            workflow_id,
        )