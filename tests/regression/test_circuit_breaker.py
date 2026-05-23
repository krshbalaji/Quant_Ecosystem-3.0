import pytest
from quant_ecosystem.execution.execution_router import MultiBrokerRouter


class FailingBroker:
    def place_order(self, **kwargs):
        raise RuntimeError("timeout")


def test_circuit_breaker_locks_after_failures():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = FailingBroker()

    locked = False

    for i in range(10):
        try:
            router.place_order(
                symbol=f"NSE:ITC{i}-EQ",   # unique each time
                side="BUY",
                qty=1,
                price=300.0,
                asset_class="EQUITY",
            )
        except RuntimeError as exc:
            if "LIVE CIRCUIT BREAKER ACTIVE" in str(exc):
                locked = True
                break

    assert locked