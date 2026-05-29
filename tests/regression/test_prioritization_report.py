from quant_ecosystem.cognition.swarm import (
    PrioritizationReport,
)


def test_prioritization_report():

    report = PrioritizationReport(
        objective_count=0,
        objectives=[],
    )

    assert report.objective_count == 0