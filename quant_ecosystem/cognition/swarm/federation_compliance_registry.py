# quant_ecosystem/cognition/swarm/federation_compliance_registry.py

from typing import List

from .compliance_violation import (
    ComplianceViolation,
)


class FederationComplianceRegistry:

    def __init__(self):
        self._violations: List[
            ComplianceViolation
        ] = []

    def register(
        self,
        violation: ComplianceViolation,
    ) -> None:

        self._violations.append(
            violation
        )

    def violations(self):

        return list(
            self._violations
        )

    def count(self) -> int:

        return len(
            self._violations
        )