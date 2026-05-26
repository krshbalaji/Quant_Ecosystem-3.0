from quant_ecosystem.execution.telemetry.execution_metrics import (
    ExecutionMetrics,
)


def test_metrics():
    m = ExecutionMetrics()

    m.record_attempt()
    m.record_success()
    m.record_failure()

    snap = m.snapshot()

    assert snap["orders_attempted"] == 1
    assert snap["orders_completed"] == 1
    assert snap["orders_failed"] == 1