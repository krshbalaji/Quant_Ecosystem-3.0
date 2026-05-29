from typing import List

from .prioritized_objective import (
    PrioritizedObjective,
)


class FederationRoadmapRegistry:

    def __init__(self):
        self._objectives: List[
            PrioritizedObjective
        ] = []

    def register(
        self,
        objective: PrioritizedObjective,
    ) -> None:

        self._objectives.append(
            objective
        )

    def objectives(self):

        return sorted(
            self._objectives,
            key=lambda x: x.priority_rank,
        )