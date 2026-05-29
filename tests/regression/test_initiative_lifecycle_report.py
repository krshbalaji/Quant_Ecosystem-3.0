from quant_ecosystem.cognition.swarm import (
    InitiativeLifecycleReport,
)


def test_lifecycle_report():

    report = (
        InitiativeLifecycleReport(
            total_records=5,
            active_records=2,
        )
    )

    assert report.total_records == 5