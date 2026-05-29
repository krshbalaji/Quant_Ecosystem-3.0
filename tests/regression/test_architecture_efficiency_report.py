from quant_ecosystem.cognition.swarm import (
    ArchitectureEfficiencyReport,
)


def test_efficiency_report():

    report = (
        ArchitectureEfficiencyReport(
            average_efficiency=0.8,
            category_count=2,
        )
    )

    assert report.category_count == 2