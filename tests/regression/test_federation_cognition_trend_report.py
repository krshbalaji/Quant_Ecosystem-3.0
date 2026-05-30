from quant_ecosystem.cognition.swarm import (
    FederationCognitionTrendReport,
)


def test_trend_report():

    report = FederationCognitionTrendReport(
        direction="IMPROVING",
        change_rate=0.25,
        sample_count=5,
    )

    assert report.direction == "IMPROVING"