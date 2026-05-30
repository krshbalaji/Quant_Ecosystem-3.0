from quant_ecosystem.cognition.swarm import (
    FederationCognitionAlertReport,
    FederationCognitionResponseEngine,
)


def test_response_engine():

    alert = FederationCognitionAlertReport(
        level="DECLINING_ALERT",
        alert_count=1,
    )

    report = (
        FederationCognitionResponseEngine()
        .evaluate(alert)
    )

    assert (
        report.recommended_action
        == "EXECUTE_IMPROVEMENT_PLAN"
    )