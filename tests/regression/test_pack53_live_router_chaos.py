import pytest

from quant_ecosystem.execution.execution_router import (
    MultiBrokerRouter,
)

from quant_ecosystem.execution.chaos.chaos_profiles import (
    ChaosProfile,
)


class DummyBroker:
    def place_order(self, **kwargs):
        return {
            "status": "TRADE",
            "order_id": "LIVE-OK-001",
        }

    def get_orders(self):
        return []


def build_router():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = DummyBroker()
    return router


def test_live_timeout_chaos():
    router = build_router()

    router._failure_injector.enable(
        ChaosProfile.TIMEOUT
    )

    with pytest.raises(
        RuntimeError,
        match="Injected timeout failure",
    ):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )


def test_live_disconnect_chaos():
    router = build_router()

    router._failure_injector.enable(
        ChaosProfile.DISCONNECT
    )

    with pytest.raises(
        RuntimeError,
        match="Injected disconnect failure",
    ):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )


def test_live_false_success_blocked():
    router = build_router()

    router._failure_injector.enable(
        ChaosProfile.FALSE_SUCCESS
    )

    with pytest.raises(RuntimeError):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )


def test_live_partial_fill_valid():
    router = build_router()

    original_inject = router._failure_injector.inject

    def fyers_partial():
        return {
            "status": "PARTIAL",
            "filledQty": 1,
            "remainingQuantity": 0,
            "tradedPrice": 300.0,
            "order_id": "PARTIAL-001",
        }

    router._failure_injector.enable(
        ChaosProfile.PARTIAL_FILL
    )

    router._failure_injector.inject = fyers_partial

    result = router.place_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
        asset_class="EQUITY",
    )

    router._failure_injector.inject = original_inject

    assert result["status"] == "PARTIAL"
    assert result["filled_qty"] == 1


def test_live_valid_trade_still_passes():
    router = build_router()

    result = router.place_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
        asset_class="EQUITY",
    )

    assert result["order_id"] == "LIVE-OK-001"