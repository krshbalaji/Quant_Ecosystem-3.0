from quant_ecosystem.cognition.swarm import (
    ReadinessReport,
)


def test_readiness_report():

    report = ReadinessReport(
        operationally_ready=True,
        readiness_score=1.0,
    )

    assert report.operationally_ready