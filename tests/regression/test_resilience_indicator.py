from quant_ecosystem.cognition.swarm import (
    ResilienceIndicator,
)


def test_resilience_indicator():

    indicator = ResilienceIndicator(
        category_name="execution",
        resilience_score=4.0,
    )

    assert (
        indicator.resilience_score
        == 4.0
    )