from quant_ecosystem.cognition.swarm import (
    PredictabilitySignal,
    FederationPredictabilityRegistry,
    FederationPredictabilityEngine,
)


def test_engine():

    registry = FederationPredictabilityRegistry()

    registry.register(
        PredictabilitySignal(
            federation_id="FED",
            predictability_score=0.75,
            source="forecast",
        )
    )

    registry.register(
        PredictabilitySignal(
            federation_id="FED",
            predictability_score=0.95,
            source="analytics",
        )
    )

    report = (
        FederationPredictabilityEngine()
        .evaluate(registry)
    )

    assert report.signal_count == 2
    assert report.strongest_source == "analytics"