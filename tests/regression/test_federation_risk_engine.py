from quant_ecosystem.cognition.swarm import (
    FederationRiskEngine,
    FederationRiskRegistry,
    RiskIndicator,
)


def test_risk_engine():

    registry = (
        FederationRiskRegistry()
    )

    registry.register(
        RiskIndicator(
            category_name="execution",
            risk_score=2.0,
        )
    )

    registry.register(
        RiskIndicator(
            category_name="decision",
            risk_score=5.0,
        )
    )

    report = (
        FederationRiskEngine()
        .evaluate(registry)
    )

    assert (
        report.highest_risk_category
        == "decision"
    )

    assert (
        report.highest_risk_score
        == 5.0
    )