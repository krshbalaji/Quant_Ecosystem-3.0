from quant_ecosystem.autonomous_risk import (
    self_healing_engine,
    autonomous_controls,
)


def test_diagnose_broker():
    result = (
        self_healing_engine
        .diagnose(
            "NORMAL",
            broker_connected=False,
        )
    )

    assert result == "BROKER_RECOVERY"


def test_diagnose_risk():
    result = (
        self_healing_engine
        .diagnose(
            "CRITICAL"
        )
    )

    assert result == "RISK_CONTAINMENT"


def test_recover():
    result = (
        self_healing_engine
        .recover(
            "ENGINE_RECOVERY"
        )
    )

    assert result == "RESTART_ENGINE"


def test_kill_switch():
    result = (
        autonomous_controls
        .kill_switch(
            "CRITICAL"
        )
    )

    assert result is True


def test_resume():
    result = (
        autonomous_controls
        .can_resume(
            "NORMAL"
        )
    )

    assert result is True


def test_evaluate():
    result = (
        autonomous_controls
        .evaluate(
            "CRITICAL"
        )
    )

    assert result["kill_switch"] is True