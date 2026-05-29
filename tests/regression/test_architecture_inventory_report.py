from quant_ecosystem.cognition.swarm import (
    ArchitectureInventoryReport,
)


def test_inventory_report():

    report = (
        ArchitectureInventoryReport(
            total_components=10,
            unique_types=3,
        )
    )

    assert report.unique_types == 3