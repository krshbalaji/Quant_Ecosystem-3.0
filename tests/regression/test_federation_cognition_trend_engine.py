from quant_ecosystem.cognition.swarm import (
    FederationCognitionTrendPoint,
    FederationCognitionTrendEngine,
)


def test_trend_engine_improving():

    points = [
        FederationCognitionTrendPoint(
            timestamp="t1",
            cognition_index=0.40,
        ),
        FederationCognitionTrendPoint(
            timestamp="t2",
            cognition_index=0.80,
        ),
    ]

    report = (
        FederationCognitionTrendEngine()
        .evaluate(points)
    )

    assert report.direction == "IMPROVING"
    assert report.sample_count == 2


def test_trend_engine_declining():

    points = [
        FederationCognitionTrendPoint(
            timestamp="t1",
            cognition_index=0.90,
        ),
        FederationCognitionTrendPoint(
            timestamp="t2",
            cognition_index=0.30,
        ),
    ]

    report = (
        FederationCognitionTrendEngine()
        .evaluate(points)
    )

    assert report.direction == "DECLINING"