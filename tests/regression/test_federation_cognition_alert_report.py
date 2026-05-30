from quant_ecosystem.cognition.swarm import (
    FederationCognitionAlertReport,
)


def test_alert_report():

    report = FederationCognitionAlertReport(
        level="IMPROVING_ALERT",
        alert_count=1,
    )

    assert report.alert_count == 1