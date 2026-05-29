from typing import Dict

from .workflow_definition import (
    WorkflowDefinition,
)


class WorkflowRegistry:

    def __init__(self):
        self._workflows: Dict[
            str,
            WorkflowDefinition,
        ] = {}

    def register(
        self,
        workflow: WorkflowDefinition,
    ) -> None:

        self._workflows[
            workflow.workflow_id
        ] = workflow

    def get(
        self,
        workflow_id: str,
    ):

        return self._workflows.get(
            workflow_id
        )