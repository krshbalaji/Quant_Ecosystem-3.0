from quant_ecosystem.cognition.swarm import (
    AdaptationSignal,
    FederationAdaptationRegistry,
)


def test_registry():

    registry = FederationAdaptationRegistry()

    registry.register(
        AdaptationSignal(
            federation_id="FED",
            adaptation_score=0.80,
            source="runtime",
        )
    )

    assert len(
        registry.signals()
    ) == 1