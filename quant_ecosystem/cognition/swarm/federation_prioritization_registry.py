from typing import List

from .strategic_objective import (
    StrategicObjective,
)


class FederationPrioritizationRegistry:

    def __init__(self):
        self._objectives: List[
            StrategicObjective
        ] = []

    def register(
        self,
        objective: StrategicObjective,
    ) -> None:

        self._objectives.append(
            objective
        )

    def objectives(self):

        return list(
            self._objectives
        )

    def count(self) -> int:

        return len(
            self._objectives
        )