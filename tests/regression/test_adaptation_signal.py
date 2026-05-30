from quant_ecosystem.cognition.swarm import (
    AdaptationSignal,
)


def test_adaptation_signal():

    signal = AdaptationSignal(
        federation_id="FED",
        adaptation_score=0.92,
        source="runtime",
    )

    assert signal.source == "runtime"