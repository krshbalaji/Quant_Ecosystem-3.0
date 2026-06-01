from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .maturity_assessment import (
    MaturityAssessment,
)


class FederationMaturityRegistry(
    AppendRegistry[
        MaturityAssessment
    ]
):

    def assessments(
        self,
    ) -> list[
        MaturityAssessment
    ]:

        return self.entries()