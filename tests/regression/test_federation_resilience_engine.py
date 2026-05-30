from quant_ecosystem.cognition.swarm import (
    FederationResilienceEngine,
    FederationResilienceRegistry,
    ResilienceIndicator,
)


def test_resilience_engine():

    registry = (
        FederationResilienceRegistry()
    )

    registry.register(
        ResilienceIndicator(
            category_name="execution",
            resilience_score=4.0,
        )
    )

    registry.register(
        ResilienceIndicator(
            category_name="decision",
            resilience_score=6.0,
        )
    )

    report = (
        FederationResilienceEngine()
        .evaluate(registry)
    )

    assert (
        report.strongest_category
        == "decision"
    )

    assert (
        report.resilience_score
        == 6.0
    )