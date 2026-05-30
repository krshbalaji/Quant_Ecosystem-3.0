from quant_ecosystem.cognition.swarm import (
    ImprovementCandidate,
    FederationImprovementEngine,
    FederationImprovementRegistry,
)


def test_improvement_engine():

    registry = (
        FederationImprovementRegistry()
    )

    registry.register(
        ImprovementCandidate(
            category_name="execution",
            improvement_score=8.0,
        )
    )

    registry.register(
        ImprovementCandidate(
            category_name="decision",
            improvement_score=10.0,
        )
    )

    report = (
        FederationImprovementEngine()
        .evaluate(registry)
    )

    assert (
        report.recommended_category
        == "decision"
    )

    assert (
        report.improvement_score
        == 10.0
    )