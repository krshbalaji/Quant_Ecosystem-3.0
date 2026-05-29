from quant_ecosystem.cognition.swarm import (
    FederationForecastRegistry,
    ForecastProjection,
)


def test_forecast_registry():

    registry = (
        FederationForecastRegistry()
    )

    registry.register(
        ForecastProjection(
            current_count=100,
            projected_count=120,
        )
    )

    assert registry.count() == 1