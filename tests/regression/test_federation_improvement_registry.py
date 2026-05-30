from quant_ecosystem.cognition.swarm import (
    ImprovementCandidate,
    FederationImprovementRegistry,
)


def test_improvement_registry():

    registry = (
        FederationImprovementRegistry()
    )

    registry.register(
        ImprovementCandidate(
            category_name="execution",
            improvement_score=8.0,
        )
    )

    assert registry.count() == 1