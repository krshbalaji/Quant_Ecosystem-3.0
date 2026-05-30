from quant_ecosystem.cognition.swarm import (
    FederationCognitionForecast,
)


def test_forecast():

    forecast = FederationCognitionForecast(
        projected_index=1.2,
        horizon=3,
    )

    assert forecast.horizon == 3