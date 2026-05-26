import pytest

from quant_ecosystem.execution.execution_router import (
    MultiBrokerRouter,
)


class DummyBroker:
    def place_order(self, **kwargs):
        return {
            "status": "TRADE",
            "order_id": "OK123",
            "s": "ok",
        }

    def get_orders(self):
        return [
            {"order_id": "OK123"}
        ]


def test_duplicate_order_blocked():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = DummyBroker()

    # widen determinism
    router._duplicate_guard._window = 999999

    router.place_order(
        symbol="NSE:ITC-EQ",
        side="BUY",
        qty=1,
        price=300.0,
        asset_class="EQUITY",
    )

    with pytest.raises(RuntimeError):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )