from quant_ecosystem.cognition.swarm import (
    ArchitectureDriftReport,
)


def test_drift_report():

    report = (
        ArchitectureDriftReport(
            component_growth=5,
            growth_detected=True,
        )
    )

    assert report.growth_detected