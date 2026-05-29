from quant_ecosystem.cognition.swarm import (
    FederationMaturityRegistry,
    MaturityAssessment,
    MaturityLevel,
)


def test_maturity_registry():

    registry = (
        FederationMaturityRegistry()
    )

    registry.register(
        MaturityAssessment(
            domain="governance",
            maturity_level=(
                MaturityLevel.OPERATIONAL
            ),
        )
    )

    assert registry.count() == 1