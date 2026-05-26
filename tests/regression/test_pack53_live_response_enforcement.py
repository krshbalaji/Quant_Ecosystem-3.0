import pytest

from quant_ecosystem.execution.orchestrators.live_execution_orchestrator import (
    LiveExecutionOrchestrator,
)

from quant_ecosystem.execution.contracts.broker_response_validator import (
    BrokerResponseValidator,
)


class DummyBreaker:
    def reset(self):
        pass

    def record_failure(self):
        pass


class DummyHealth:
    def mark_healthy(self, broker):
        pass

    def mark_unhealthy(self, broker):
        pass


def test_invalid_live_response_blocked():
    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
        response_validator=BrokerResponseValidator(),
    )

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
            execution_fn=lambda: {
                "status": "SUCCESS"
            },
        )


def test_valid_live_response_allowed():
    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
        response_validator=BrokerResponseValidator(),
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
        execution_fn=lambda: {
            "status": "TRADE",
            "order_id": "OK123",
        },
    )

    assert result["order_id"] == "OK123"