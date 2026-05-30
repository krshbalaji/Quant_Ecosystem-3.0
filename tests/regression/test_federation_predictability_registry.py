from quant_ecosystem.cognition.swarm import (
    PredictabilitySignal,
    FederationPredictabilityRegistry,
)


def test_registry():

    registry = FederationPredictabilityRegistry()

    registry.register(
        PredictabilitySignal(
            federation_id="FED",
            predictability_score=0.80,
            source="forecast",
        )
    )

    assert len(
        registry.signals()
    ) == 1