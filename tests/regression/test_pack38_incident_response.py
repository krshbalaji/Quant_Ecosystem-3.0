from quant_ecosystem.observability import (
    diagnostic_engine,
    incident_response_orchestrator,
)


def test_broker_outage():
    result = (
        diagnostic_engine.diagnose(
            "NORMAL",
            0,
            broker_connected=False,
        )
    )

    assert result["incident"] == "BROKER_OUTAGE"


def test_execution_failure():
    result = (
        diagnostic_engine.diagnose(
            "NORMAL",
            0,
            execution_alive=False,
        )
    )

    assert result["incident"] == "EXECUTION_FAILURE"


def test_error_spike():
    result = (
        diagnostic_engine.diagnose(
            "NORMAL",
            8,
        )
    )

    assert result["incident"] == "ERROR_SPIKE"


def test_response_plan():
    result = (
        incident_response_orchestrator
        .response_plan(
            "SYSTEM_STRESS"
        )
    )

    assert result == "THROTTLE_LOAD"


def test_evaluate():
    result = (
        incident_response_orchestrator
        .evaluate(
            "CRITICAL",
            12,
        )
    )

    assert result["action"] == "THROTTLE_LOAD"