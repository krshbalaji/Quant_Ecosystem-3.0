from quant_ecosystem.execution.telemetry.execution_audit import (
    ExecutionAudit,
)


def test_audit_record():
    audit = ExecutionAudit()

    audit.record(
        "ORDER",
        {"symbol": "TEST"},
    )

    assert len(audit.all_events()) == 1