from quant_ecosystem.canonical.canonical_router import (
    CanonicalRouter,
)

from quant_ecosystem.canonical.exceptions import (
    UnsupportedProviderError,
)

from quant_ecosystem.canonical.normalizers.base_normalizer import (
    BaseCanonicalNormalizer,
)


class DummyNormalizer(BaseCanonicalNormalizer):

    @property
    def provider_name(self):
        return "dummy"

    def normalize_ltp(self, payload, symbol, market, asset_class="EQUITY"):
        return {"ok": "ltp"}

    def normalize_quote(self, payload, symbol, market, asset_class="EQUITY"):
        return {"ok": "quote"}

    def normalize_ohlcv(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
        interval="1m",
    ):
        return {"ok": "ohlcv"}

    def normalize_orderbook(
        self,
        payload,
        symbol,
        market,
        asset_class="EQUITY",
    ):
        return {"ok": "orderbook"}

    def normalize_balance(self, payload):
        return {"ok": "balance"}

    def normalize_position(self, payload):
        return {"ok": "position"}

    def normalize_order(self, payload):
        return {"ok": "order"}

    def normalize_execution(self, payload):
        return {"ok": "execution"}


def test_provider_registration():
    router = CanonicalRouter()

    assert router.has_provider("fyers")
    assert router.has_provider("groww")
    assert router.has_provider("viewtrade")
    assert router.has_provider("coinswitch")


def test_provider_lookup():
    router = CanonicalRouter()

    obj = router.get("fyers")

    assert obj.provider_name == "fyers"


def test_unsupported_provider_rejected():
    router = CanonicalRouter()

    try:
        router.get("ghostbroker")
        assert False
    except UnsupportedProviderError:
        assert True


def test_ltp_normalization():
    router = CanonicalRouter()

    out = router.normalize_ltp(
        provider="fyers",
        payload={"ltp": 2500},
        symbol="NSE:RELIANCE-EQ",
        market="INDIA",
    )

    assert out.price == 2500


def test_quote_normalization():
    router = CanonicalRouter()

    out = router.normalize_quote(
        provider="fyers",
        payload={
            "bid": 100,
            "ask": 101,
            "open": 95,
            "high": 110,
            "low": 94,
            "close": 99,
            "prev_close": 98,
        },
        symbol="NSE:ITC-EQ",
        market="INDIA",
    )

    assert out.bid == 100
    assert out.ask == 101


def test_ohlcv_normalization():
    router = CanonicalRouter()

    out = router.normalize_ohlcv(
        provider="fyers",
        payload={
            "candles": [
                [1710000000, 100, 110, 95, 105, 1000]
            ]
        },
        symbol="NSE:SBIN-EQ",
        market="INDIA",
    )

    assert len(out.bars) == 1


def test_orderbook_normalization():
    router = CanonicalRouter()

    out = router.normalize_orderbook(
        provider="fyers",
        payload={
            "bids": [
                {"price": 100, "qty": 10}
            ],
            "asks": [
                {"price": 101, "qty": 8}
            ],
        },
        symbol="NSE:TCS-EQ",
        market="INDIA",
    )

    assert len(out.bids) == 1
    assert len(out.asks) == 1


def test_balance_normalization():
    router = CanonicalRouter()

    out = router.normalize_balance(
        provider="fyers",
        payload={
            "fund_limit": {
                "equityAmount": 100000,
                "limit": 120000,
                "utilizedAmount": 20000,
            }
        },
    )

    assert out.cash == 100000


def test_position_normalization():
    router = CanonicalRouter()

    out = router.normalize_position(
        provider="fyers",
        payload={
            "symbol": "NSE:INFY-EQ",
            "qty": 5,
            "avgPrice": 1500,
            "ltp": 1510,
        },
    )

    assert out.qty == 5


def test_order_normalization():
    router = CanonicalRouter()

    out = router.normalize_order(
        provider="fyers",
        payload={
            "id": "ABC123",
            "symbol": "NSE:HDFCBANK-EQ",
            "side": "BUY",
            "qty": 10,
            "status": "OPEN",
        },
    )

    assert out.order_id == "ABC123"


def test_execution_normalization():
    router = CanonicalRouter()

    out = router.normalize_execution(
        provider="fyers",
        payload={
            "tradeId": "TR001",
            "orderId": "OD001",
            "symbol": "NSE:AXISBANK-EQ",
            "qty": 2,
            "tradePrice": 1100,
        },
    )

    assert out.execution_id == "TR001"


def test_plugin_registration():
    router = CanonicalRouter()

    router.register(DummyNormalizer())

    assert router.has_provider("dummy")

    out = router.normalize_order(
        provider="dummy",
        payload={},
    )

    assert out["ok"] == "order"