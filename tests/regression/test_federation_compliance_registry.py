from quant_ecosystem.cognition.swarm import (
    ComplianceViolation,
    FederationComplianceRegistry,
)


def test_compliance_registry():

    registry = (
        FederationComplianceRegistry()
    )

    registry.register(
        ComplianceViolation(
            rule_id="R1",
            severity=0.8,
        )
    )

    assert registry.count() == 1