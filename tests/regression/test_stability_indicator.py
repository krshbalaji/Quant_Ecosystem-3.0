from quant_ecosystem.cognition.swarm import (
    StabilityIndicator,
)


def test_stability_indicator():

    indicator = StabilityIndicator(
        federation_id="FED",
        stability_score=0.9,
        source="ops",
    )

    assert indicator.source == "ops"