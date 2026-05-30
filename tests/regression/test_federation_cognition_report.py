from quant_ecosystem.cognition.swarm import (
    FederationCognitionReport,
)


def test_report():

    report = FederationCognitionReport(
        cognition_index=0.8,
        strongest_dimension="trust",
        weakest_dimension="risk",
    )

    assert report.cognition_index == 0.8