from quant_ecosystem.cognition.swarm import (
    FederationMaturityEngine,
    FederationMaturityRegistry,
    MaturityAssessment,
    MaturityLevel,
)


def test_maturity_engine():

    registry = (
        FederationMaturityRegistry()
    )

    registry.register(
        MaturityAssessment(
            domain="audit",
            maturity_level=(
                MaturityLevel.OPERATIONAL
            ),
        )
    )

    report = (
        FederationMaturityEngine()
        .evaluate(registry)
    )

    assert (
        report.maturity_level
        == MaturityLevel.EMERGING
    )