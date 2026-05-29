from quant_ecosystem.cognition.swarm import (
    FederationForecastEngine,
    FederationForecastRegistry,
    ForecastProjection,
)


def test_forecast_engine():

    registry = (
        FederationForecastRegistry()
    )

    registry.register(
        ForecastProjection(
            current_count=100,
            projected_count=125,
        )
    )

    report = (
        FederationForecastEngine()
        .evaluate(
            registry
        )
    )

    assert report.projected_growth == 25
    assert report.projected_total == 125