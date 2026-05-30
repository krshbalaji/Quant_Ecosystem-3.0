from quant_ecosystem.cognition.swarm import (
    FederationCognitionTrendReport,
    FederationCognitionForecastEngine,
)


def test_forecast_engine():

    trend = FederationCognitionTrendReport(
        direction="IMPROVING",
        change_rate=0.10,
        sample_count=5,
    )

    report = (
        FederationCognitionForecastEngine()
        .forecast(
            current_index=0.80,
            trend=trend,
            horizon=2,
        )
    )

    assert report.direction == "IMPROVING"
    assert report.projected_index == 1.0