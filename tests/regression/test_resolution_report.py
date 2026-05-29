from quant_ecosystem.cognition.swarm import (
    ResolutionReport,
)


def test_resolution_report():

    report = ResolutionReport(
        collision_count=2,
        resolution_count=2,
    )

    assert report.resolution_count == 2