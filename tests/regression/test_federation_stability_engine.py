from quant_ecosystem.cognition.swarm import (
    StabilityIndicator,
    FederationStabilityRegistry,
    FederationStabilityEngine,
)


def test_engine():

    registry = FederationStabilityRegistry()

    registry.register(
        StabilityIndicator(
            federation_id="FED",
            stability_score=0.8,
            source="ops",
        )
    )

    registry.register(
        StabilityIndicator(
            federation_id="FED",
            stability_score=1.0,
            source="risk",
        )
    )

    report = (
        FederationStabilityEngine()
        .evaluate(registry)
    )

    assert report.indicator_count == 2
    assert report.strongest_source == "risk"