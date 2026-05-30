from quant_ecosystem.cognition.swarm import (
    FederationCognitionForecastReport,
)


def test_forecast_report():

    report = FederationCognitionForecastReport(
        current_index=0.8,
        projected_index=1.0,
        direction="IMPROVING",
        horizon=2,
    )

    assert report.direction == "IMPROVING"