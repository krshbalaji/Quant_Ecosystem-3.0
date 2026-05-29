from quant_ecosystem.cognition.swarm import (
    ArchitectureOptimizationReport,
)


def test_optimization_report():

    report = (
        ArchitectureOptimizationReport(
            target_category="governance",
            component_count=20,
        )
    )

    assert report.component_count == 20