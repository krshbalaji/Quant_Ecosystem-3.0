from typing import List

from .maturity_assessment import (
    MaturityAssessment,
)


class FederationMaturityRegistry:

    def __init__(self):
        self._assessments: List[
            MaturityAssessment
        ] = []

    def register(
        self,
        assessment: MaturityAssessment,
    ) -> None:

        self._assessments.append(
            assessment
        )

    def count(self) -> int:

        return len(
            self._assessments
        )

    def assessments(self):

        return list(
            self._assessments
        )