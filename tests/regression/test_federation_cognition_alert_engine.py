from quant_ecosystem.cognition.swarm import (
    FederationCognitionForecastReport,
    FederationCognitionAlertEngine,
)


def test_alert_engine():

    forecast = FederationCognitionForecastReport(
        current_index=0.80,
        projected_index=1.00,
        direction="IMPROVING",
        horizon=2,
    )

    report = (
        FederationCognitionAlertEngine()
        .evaluate(forecast)
    )

    assert (
        report.level
        == "IMPROVING_ALERT"
    )