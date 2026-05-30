# tests/regression/test_federation_compliance_engine.py

from quant_ecosystem.cognition.swarm import (
    ComplianceViolation,
    FederationComplianceEngine,
    FederationComplianceRegistry,
)


def test_compliance_engine():

    registry = (
        FederationComplianceRegistry()
    )

    registry.register(
        ComplianceViolation(
            rule_id="R1",
            severity=0.4,
        )
    )

    registry.register(
        ComplianceViolation(
            rule_id="R2",
            severity=0.9,
        )
    )

    report = (
        FederationComplianceEngine()
        .evaluate(registry)
    )

    assert (
        report.violation_count
        == 2
    )

    assert (
        report.highest_severity
        == 0.9
    )