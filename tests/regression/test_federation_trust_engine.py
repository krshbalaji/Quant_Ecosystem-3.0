from quant_ecosystem.cognition.swarm import (
    TrustMetric,
    FederationTrustRegistry,
    FederationTrustEngine,
)


def test_engine():

    registry = FederationTrustRegistry()

    registry.register(
        TrustMetric(
            federation_id="FED",
            trust_score=0.80,
            source="ops",
        )
    )

    registry.register(
        TrustMetric(
            federation_id="FED",
            trust_score=1.00,
            source="audit",
        )
    )

    report = (
        FederationTrustEngine()
        .evaluate(registry)
    )

    assert report.metric_count == 2
    assert report.strongest_source == "audit"