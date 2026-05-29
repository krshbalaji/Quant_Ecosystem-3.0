from typing import List

from .decision_candidate import (
    DecisionCandidate,
)


class FederationDecisionRegistry:

    def __init__(self):
        self._candidates: List[
            DecisionCandidate
        ] = []

    def register(
        self,
        candidate: DecisionCandidate,
    ) -> None:

        self._candidates.append(
            candidate
        )

    def candidates(self):

        return list(
            self._candidates
        )

    def count(self):

        return len(
            self._candidates
        )