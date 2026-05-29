from typing import List

from .workflow_step import WorkflowStep


class WorkflowIntegrationRegistry:

    def __init__(self):
        self._steps: List[
            WorkflowStep
        ] = []

    def register(
        self,
        step: WorkflowStep,
    ) -> None:

        self._steps.append(step)

    def enabled_steps(self):

        return [
            step
            for step in self._steps
            if step.enabled
        ]