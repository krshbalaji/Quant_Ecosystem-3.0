from typing import List

from .orchestration_stage import (
    OrchestrationStage,
)


class OrchestrationRegistry:

    def __init__(self):
        self._stages: List[
            OrchestrationStage
        ] = []

    def register(
        self,
        stage: OrchestrationStage,
    ) -> None:

        self._stages.append(stage)

    def stages(self):

        return list(self._stages)

    def enabled_count(self) -> int:

        return sum(
            1
            for stage in self._stages
            if stage.enabled
        )