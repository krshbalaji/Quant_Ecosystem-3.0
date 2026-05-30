from quant_ecosystem.cognition.swarm import (
    FederationCognitionResponseReport,
)


def test_response_report():

    report = FederationCognitionResponseReport(
        recommended_action="MAINTAIN",
        response_count=1,
    )

    assert report.response_count == 1