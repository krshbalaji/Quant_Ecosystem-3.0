from quant_ecosystem.cognition.swarm import (
    TrustMetric,
    FederationTrustRegistry,
)


def test_registry():

    registry = FederationTrustRegistry()

    registry.register(
        TrustMetric(
            federation_id="FED",
            trust_score=0.90,
            source="ops",
        )
    )

    assert len(
        registry.metrics()
    ) == 1