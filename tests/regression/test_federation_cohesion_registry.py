from quant_ecosystem.cognition.swarm import (
    CohesionSignal,
    FederationCohesionRegistry,
)


def test_registry():

    registry = FederationCohesionRegistry()

    registry.register(
        CohesionSignal(
            federation_id="FED",
            cohesion_score=0.80,
            source="alignment",
        )
    )

    assert len(
        registry.signals()
    ) == 1