from typing import List

from .improvement_candidate import (
    ImprovementCandidate,
)


class FederationImprovementRegistry:

    def __init__(self):
        self._candidates: List[
            ImprovementCandidate
        ] = []

    def register(
        self,
        candidate: ImprovementCandidate,
    ) -> None:

        self._candidates.append(
            candidate
        )

    def candidates(self):

        return list(
            self._candidates
        )

    def count(self) -> int:

        return len(
            self._candidates
        )