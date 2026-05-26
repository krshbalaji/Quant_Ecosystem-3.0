import pytest

from quant_ecosystem.execution.orchestrators.live_execution_orchestrator import (
    LiveExecutionOrchestrator,
)

from quant_ecosystem.execution.chaos.failure_injector import (
    FailureInjector,
)

from quant_ecosystem.execution.chaos.chaos_profiles import (
    ChaosProfile,
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


def test_false_success_chaos():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.FALSE_SUCCESS
    )

    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
        failure_injector=injector,
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
            execution_fn=lambda: {},
        )


def test_false_success_chaos():
    injector = FailureInjector()

    injector.enable(
        ChaosProfile.FALSE_SUCCESS
    )

    orch = LiveExecutionOrchestrator(
        DummyBreaker(),
        DummyHealth(),
        None,
        failure_injector=injector,
    )

    with pytest.raises(
        RuntimeError,
        match="Missing order_id",
    ):
        orch.execute(
            broker=object(),
            broker_name="x",
            normalized_symbol="INFY",
            symbol="INFY",
            side="BUY",
            qty=1,
            price=100,
            asset_class="EQUITY",
            execution_fn=lambda: {},
        )
