from quant_ecosystem.cognition.swarm import (
    CohesionSignal,
)


def test_cohesion_signal():

    signal = CohesionSignal(
        federation_id="FED",
        cohesion_score=0.90,
        source="alignment",
    )

    assert signal.source == "alignment"