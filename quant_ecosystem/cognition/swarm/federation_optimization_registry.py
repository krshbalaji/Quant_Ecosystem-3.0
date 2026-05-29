from typing import List

from .optimization_candidate import (
    OptimizationCandidate,
)


class FederationOptimizationRegistry:

    def __init__(self):
        self._candidates: List[
            OptimizationCandidate
        ] = []

    def register(
        self,
        candidate: OptimizationCandidate,
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