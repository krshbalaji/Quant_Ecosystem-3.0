from quant_ecosystem.cognition.swarm import (
    CohesionSignal,
    FederationCohesionRegistry,
    FederationCohesionEngine,
)


def test_engine():

    registry = FederationCohesionRegistry()

    registry.register(
        CohesionSignal(
            federation_id="FED",
            cohesion_score=0.70,
            source="alignment",
        )
    )

    registry.register(
        CohesionSignal(
            federation_id="FED",
            cohesion_score=0.95,
            source="governance",
        )
    )

    report = (
        FederationCohesionEngine()
        .evaluate(registry)
    )

    assert report.signal_count == 2
    assert report.strongest_source == "governance"