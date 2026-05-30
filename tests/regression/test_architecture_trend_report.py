from quant_ecosystem.cognition.swarm import (
    ArchitectureTrendDirection,
    ArchitectureTrendReport,
)


def test_trend_report():

    report = ArchitectureTrendReport(
        trend_direction=(
            ArchitectureTrendDirection.GROWING
        ),
        net_change=5,
    )

    assert report.net_change == 5