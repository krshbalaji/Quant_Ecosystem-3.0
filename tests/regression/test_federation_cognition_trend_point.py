from quant_ecosystem.cognition.swarm import (
    FederationCognitionTrendPoint,
)


def test_trend_point():

    point = FederationCognitionTrendPoint(
        timestamp="2026-01-01",
        cognition_index=0.75,
    )

    assert point.cognition_index == 0.75