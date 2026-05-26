from quant_ecosystem.execution.orchestrators.live_execution_orchestrator import (
    LiveExecutionOrchestrator,
)


class DummyBreaker:
    def __init__(self):
        self.reset_called = False
        self.failure_called = False

    def reset(self):
        self.reset_called = True

    def record_failure(self):
        self.failure_called = True


class DummyHealth:
    def __init__(self):
        self.good = False
        self.bad = False

    def mark_healthy(self, broker):
        self.good = True

    def mark_unhealthy(self, broker):
        self.bad = True


def test_live_execution_success():
    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
    )

    result = orch.execute(
        broker=object(),
        broker_name="x",
        normalized_symbol="INFY",
        symbol="INFY",
        side="BUY",
        qty=1,
        price=100,
        asset_class="EQUITY",
        execution_fn=lambda: {"id": "ABC"},
    )

    assert result["order_id"] == "ABC"


def test_live_execution_failure():
    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
    )

    def boom():
        raise RuntimeError("FAIL")

    import pytest

    with pytest.raises(RuntimeError):
        orch.execute(
            broker=object(),
            broker_name="x",
            normalized_symbol="INFY",
            symbol="INFY",
            side="BUY",
            qty=1,
            price=100,
            asset_class="EQUITY",
            execution_fn=boom,
        )