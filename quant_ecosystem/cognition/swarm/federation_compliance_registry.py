from quant_ecosystem.core.append_registry import (
    AppendRegistry,
)

from .compliance_violation import (
    ComplianceViolation,
)


class FederationComplianceRegistry(
    AppendRegistry[
        ComplianceViolation
    ]
):

    def violations(
        self,
    ) -> list[ComplianceViolation]:

        return self.entries()