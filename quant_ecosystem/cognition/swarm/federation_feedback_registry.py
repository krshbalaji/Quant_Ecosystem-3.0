from typing import List

from .execution_feedback import (
    ExecutionFeedback,
)


class FederationFeedbackRegistry:

    def __init__(self):
        self._feedback: List[
            ExecutionFeedback
        ] = []

    def register(
        self,
        feedback: ExecutionFeedback,
    ) -> None:

        self._feedback.append(
            feedback
        )

    def feedback(self):

        return list(
            self._feedback
        )

    def count(self) -> int:

        return len(
            self._feedback
        )