from quant_ecosystem.cognition.swarm import (
    ArchitectureDensityReport,
)


def test_density_report():

    report = (
        ArchitectureDensityReport(
            densest_category="governance",
            component_count=10,
        )
    )

    assert (
        report.densest_category
        == "governance"
    )

    assert (
        report.component_count
        == 10
    )