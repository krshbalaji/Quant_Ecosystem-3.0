from quant_ecosystem.cognition.swarm import (
    AdaptationSignal,
    FederationAdaptationRegistry,
    FederationAdaptationEngine,
)


def test_engine():

    registry = FederationAdaptationRegistry()

    registry.register(
        AdaptationSignal(
            federation_id="FED",
            adaptation_score=0.70,
            source="runtime",
        )
    )

    registry.register(
        AdaptationSignal(
            federation_id="FED",
            adaptation_score=0.95,
            source="policy",
        )
    )

    report = (
        FederationAdaptationEngine()
        .evaluate(registry)
    )

    assert report.signal_count == 2
    assert report.strongest_source == "policy"