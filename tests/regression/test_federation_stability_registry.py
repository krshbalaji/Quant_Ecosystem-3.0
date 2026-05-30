from quant_ecosystem.cognition.swarm import (
    StabilityIndicator,
    FederationStabilityRegistry,
)


def test_registry():

    registry = FederationStabilityRegistry()

    registry.register(
        StabilityIndicator(
            federation_id="FED",
            stability_score=0.8,
            source="ops",
        )
    )

    assert len(
        registry.indicators()
    ) == 1