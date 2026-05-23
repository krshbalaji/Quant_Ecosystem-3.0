from quant_ecosystem.execution.execution_router import MultiBrokerRouter


class DummyBroker:
    def place_order(self, **kwargs):
        return {"status": "TRADE", "order_id": "OK"}


def test_india_equity_routes_to_available_broker():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["groww"] = DummyBroker()

    broker = router._select("EQUITY", "INDIA")
    assert isinstance(broker, DummyBroker)


def test_us_equity_routes_to_viewtrade():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["viewtrade"] = DummyBroker()

    broker = router._select("EQUITY", "US")
    assert isinstance(broker, DummyBroker)


def test_crypto_routes_to_coinswitch():
    router = MultiBrokerRouter(mode="LIVE")
    router._brokers["coinswitch"] = DummyBroker()

    broker = router._select("SPOT", "CRYPTO")
    assert isinstance(broker, DummyBroker)


def test_unknown_market_rejected():
    router = MultiBrokerRouter(mode="LIVE")

    try:
        router._select("EQUITY", "MARS")
        assert False
    except RuntimeError:
        assert True