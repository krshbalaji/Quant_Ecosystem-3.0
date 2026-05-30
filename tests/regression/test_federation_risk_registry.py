from quant_ecosystem.cognition.swarm import (
    FederationRiskRegistry,
    RiskIndicator,
)


def test_risk_registry():

    registry = (
        FederationRiskRegistry()
    )

    registry.register(
        RiskIndicator(
            category_name="execution",
            risk_score=2.0,
        )
    )

    assert registry.count() == 1