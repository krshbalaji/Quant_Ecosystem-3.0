import pytest

from quant_ecosystem.execution.adapter_registry import adapter_registry
from quant_ecosystem.execution.adapters import (
    FyersExecutionAdapter,
    GrowwExecutionAdapter,
    ViewTradeExecutionAdapter,
    CoinSwitchExecutionAdapter,
)

from quant_ecosystem.canonical.broker_models import (
    CanonicalOrderRequest,
    CanonicalModifyRequest,
    CanonicalCancelRequest,
)


@pytest.fixture
def reset_registry():
    adapter_registry._adapters.clear()
    yield
    adapter_registry._adapters.clear()


def test_adapter_registration(reset_registry):
    adapter_registry.register("fyers", FyersExecutionAdapter())
    assert "fyers" in adapter_registry.list_adapters()


def test_adapter_lookup(reset_registry):
    adapter_registry.register("groww", GrowwExecutionAdapter())
    adapter = adapter_registry.get("groww")
    assert adapter is not None


def test_unsupported_adapter(reset_registry):
    with pytest.raises(ValueError):
        adapter_registry.get("ghost")


def test_fyers_market_translation(reset_registry):
    adapter = FyersExecutionAdapter()

    req = CanonicalOrderRequest(
        provider="fyers",
        symbol="NSE:RELIANCE-EQ",
        side="BUY",
        qty=10,
    )

    payload = adapter.translate_order(req)

    assert payload["symbol"] == "NSE:RELIANCE-EQ"
    assert payload["qty"] == 10
    assert payload["side"] == 1


def test_groww_translation():
    adapter = GrowwExecutionAdapter()

    req = CanonicalOrderRequest(
        provider="groww",
        symbol="NSE:TCS-EQ",
        side="SELL",
        qty=5,
        price=100.0,
        order_type="LIMIT",
    )

    payload = adapter.translate_order(req)

    assert payload["instrument"] == "NSE:TCS-EQ"
    assert payload["quantity"] == 5


def test_viewtrade_translation():
    adapter = ViewTradeExecutionAdapter()

    req = CanonicalOrderRequest(
        provider="viewtrade",
        symbol="AAPL",
        side="BUY",
        qty=3,
    )

    payload = adapter.translate_order(req)

    assert payload["ticker"] == "AAPL"


def test_coinswitch_symbol_translation():
    adapter = CoinSwitchExecutionAdapter()

    req = CanonicalOrderRequest(
        provider="coinswitch",
        symbol="BTC/INR",
        side="BUY",
        qty=1,
    )

    payload = adapter.translate_order(req)

    assert payload["symbol"] == "BTC-INR"


def test_modify_translation():
    adapter = FyersExecutionAdapter()

    req = CanonicalModifyRequest(
        provider="fyers",
        order_id="OID123",
        qty=20,
        price=123.0,
    )

    payload = adapter.translate_modify(req)

    assert payload["id"] == "OID123"


def test_cancel_translation():
    adapter = FyersExecutionAdapter()

    req = CanonicalCancelRequest(
        provider="fyers",
        order_id="OID999",
    )

    payload = adapter.translate_cancel(req)

    assert payload["id"] == "OID999"


def test_invalid_qty():
    with pytest.raises(ValueError):
        CanonicalOrderRequest(
            provider="fyers",
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=0,
        )