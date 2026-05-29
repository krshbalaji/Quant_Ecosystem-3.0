from quant_ecosystem.cognition.swarm import (
    DependencyHealthReport,
)


def test_health_report():

    report = (
        DependencyHealthReport(
            healthy=True,
            dependency_density=1.0,
        )
    )

    assert report.healthy