from quant_ecosystem.cognition.swarm import (
    RiskIndicator,
)


def test_risk_indicator():

    indicator = RiskIndicator(
        category_name="execution",
        risk_score=4.5,
    )

    assert indicator.risk_score == 4.5