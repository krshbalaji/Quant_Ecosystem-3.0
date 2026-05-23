import pytest
from quant_ecosystem.execution.execution_router import MultiBrokerRouter


class FakeLiveBroker:
    def place_order(self, **kwargs):
        return {
            "s": "ok",
            "id": "REAL123"
        }

    def get_orders(self):
        return []


def test_live_reconciliation_failure():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = FakeLiveBroker()

    with pytest.raises(Exception, match="reconciliation failed"):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )