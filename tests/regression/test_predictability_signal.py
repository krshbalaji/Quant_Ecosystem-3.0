from quant_ecosystem.cognition.swarm import (
    PredictabilitySignal,
)


def test_predictability_signal():

    signal = PredictabilitySignal(
        federation_id="FED",
        predictability_score=0.93,
        source="forecast",
    )

    assert signal.source == "forecast"