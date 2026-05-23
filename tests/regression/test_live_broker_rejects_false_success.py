from unittest.mock import Mock
import pytest
from quant_ecosystem.execution.execution_router import MultiBrokerRouter

class RejectingBroker:
    def place_order(self, **kwargs):
        return {
            "s": "error",
            "message": "Broker rejected order"
        }

def test_live_broker_rejection_raises():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = RejectingBroker()

    with pytest.raises(RuntimeError, match="LIVE broker rejected order"):
        router.place_order(
            symbol="NSE:ITC-EQ",
            side="BUY",
            qty=1,
            price=300.0,
            asset_class="EQUITY",
        )