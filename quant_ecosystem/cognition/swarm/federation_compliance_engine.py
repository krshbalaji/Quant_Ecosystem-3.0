# quant_ecosystem/cognition/swarm/federation_compliance_engine.py

from .compliance_report import (
    ComplianceReport,
)
from .federation_compliance_registry import (
    FederationComplianceRegistry,
)


class FederationComplianceEngine:

    def evaluate(
        self,
        registry: FederationComplianceRegistry,
    ) -> ComplianceReport:

        if not registry.violations():

            return ComplianceReport(
                violation_count=0,
                highest_severity=0.0,
            )

        highest = max(
            item.severity
            for item in registry.violations()
        )

        return ComplianceReport(
            violation_count=(
                registry.count()
            ),
            highest_severity=highest,
        )