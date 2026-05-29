from quant_ecosystem.cognition.swarm import (
    FederationHealthReport,
)


def test_health_report():

    report = (
        FederationHealthReport(
            total_capabilities=10,
            healthy_capabilities=9,
        )
    )

    assert report.healthy_capabilities == 9