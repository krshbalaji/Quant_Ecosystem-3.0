from quant_ecosystem.monitoring.alert_orchestrator import (
    alert_orchestrator,
)


def test_route():
    assert (
        alert_orchestrator.route(
            "CRITICAL"
        )
        == "ESCALATE"
    )


def test_payload():
    result = (
        alert_orchestrator.payload(
            title="Slippage breach",
            severity="HIGH",
            details={
                "bps": 75
            },
        )
    )

    assert result["route"] == (
        "TELEGRAM_ALERT"
    )


def test_escalation():
    result = (
        alert_orchestrator.escalate(
            {
                "severity": "CRITICAL"
            }
        )
    )

    assert result["escalated"] is True