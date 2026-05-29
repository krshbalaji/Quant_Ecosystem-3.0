from typing import List

from .execution_initiative import (
    ExecutionInitiative,
)


class FederationExecutionGovernanceRegistry:

    def __init__(self):
        self._initiatives: List[
            ExecutionInitiative
        ] = []

    def register(
        self,
        initiative: ExecutionInitiative,
    ) -> None:

        self._initiatives.append(
            initiative
        )

    def initiatives(self):

        return list(
            self._initiatives
        )

    def count(self) -> int:

        return len(
            self._initiatives
        )