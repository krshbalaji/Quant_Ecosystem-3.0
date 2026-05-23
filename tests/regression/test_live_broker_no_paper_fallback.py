import pytest
from quant_ecosystem.execution.execution_router import MultiBrokerRouter


class ExplodingBroker:
    def place_order(self, **kwargs):
        raise RuntimeError("LIVE BROKER FAILURE")


class FakePaper:
    def place_order(self, **kwargs):
        return {"status": "PAPER_FILL"}


def test_live_mode_never_falls_back_to_paper():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["fyers"] = ExplodingBroker()
    router._paper = FakePaper()

    with pytest.raises(RuntimeError, match="LIVE broker execution failed"):
        router.place_order(
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=1,
            price=800.0,
            asset_class="equity",
        )