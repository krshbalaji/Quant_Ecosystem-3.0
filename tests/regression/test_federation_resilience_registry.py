from quant_ecosystem.cognition.swarm import (
    FederationResilienceRegistry,
    ResilienceIndicator,
)


def test_resilience_registry():

    registry = (
        FederationResilienceRegistry()
    )

    registry.register(
        ResilienceIndicator(
            category_name="execution",
            resilience_score=4.0,
        )
    )

    assert registry.count() == 1