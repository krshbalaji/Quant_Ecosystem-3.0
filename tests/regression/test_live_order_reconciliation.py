import pytest
from quant_ecosystem.execution.execution_router import MultiBrokerRouter
from quant_ecosystem.broker.broker_capabilities import BrokerCapabilities

class FakeLiveBroker:
    ENABLE_RECONCILIATION = True

    capabilities = BrokerCapabilities(
        broker_name="fake_live",
        supported_markets=["INDIA"],
        supported_assets=["EQUITY"],
        supports_reconciliation=True,
        supports_retry=True,
        supports_cancel_order=False,
        supports_modify_order=False,
    )

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