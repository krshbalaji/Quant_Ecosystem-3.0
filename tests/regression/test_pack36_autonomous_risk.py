from quant_ecosystem.autonomous_risk import (
    live_risk_forecaster,
    regime_risk_adapter,
    dynamic_capital_scaler,
)


def test_risk_score():
    result = (
        live_risk_forecaster
        .portfolio_risk_score(
            500000,
            10000,
            -5000,
        )
    )

    assert result > 0


def test_risk_classification():
    result = (
        live_risk_forecaster
        .classify(25)
    )

    assert result == "CRITICAL"


def test_bull_adjustment():
    result = (
        regime_risk_adapter.adjust(
            "BULL"
        )
    )

    assert result == 1.2


def test_crisis_adjustment():
    result = (
        regime_risk_adapter.adjust(
            "CRISIS"
        )
    )

    assert result == 0.4


def test_dynamic_scaling():
    result = (
        dynamic_capital_scaler.scale(
            exposure=500000,
            drawdown=10000,
            pnl=-5000,
            regime="CRISIS",
            base_capital=100000,
        )
    )

    assert (
        result["recommended_capital"]
        < 100000
    )