from quant_ecosystem.cognition.swarm import (
    ArchitectureClassificationReport,
)


def test_classification_report():

    report = (
        ArchitectureClassificationReport(
            total_components=10,
            total_categories=3,
        )
    )

    assert report.total_categories == 3