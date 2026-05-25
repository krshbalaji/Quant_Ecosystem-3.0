from quant_ecosystem.governance.decision_audit import (
    decision_audit,
)


def setup_function():
    decision_audit.clear()


def test_record():
    result = (
        decision_audit.record(
            "EXECUTION",
            {"symbol": "SBIN"},
            "approved",
        )
    )

    assert result["decision_type"] == (
        "EXECUTION"
    )


def test_history():
    decision_audit.record(
        "EXECUTION",
        {"symbol": "INFY"},
    )

    result = (
        decision_audit.history()
    )

    assert len(result) == 1


def test_clear():
    decision_audit.record(
        "TEST",
        {},
    )

    decision_audit.clear()

    assert len(
        decision_audit.history()
    ) == 0