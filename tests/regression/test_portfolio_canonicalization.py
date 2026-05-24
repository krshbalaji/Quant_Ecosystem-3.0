import pytest

from quant_ecosystem.portfolio.portfolio_adapter_registry import (
    portfolio_adapter_registry,
)

from quant_ecosystem.portfolio.adapters import (
    FyersPortfolioAdapter,
    GrowwPortfolioAdapter,
    ViewTradePortfolioAdapter,
    CoinSwitchPortfolioAdapter,
)

from quant_ecosystem.canonical.broker_models import (
    CanonicalPortfolioSnapshot,
    CanonicalBalance,
    CanonicalMarginSnapshot,
    CanonicalExposureSnapshot,
    CanonicalRiskSnapshot,
)


@pytest.fixture
def reset_registry():
    portfolio_adapter_registry.clear()
    yield
    portfolio_adapter_registry.clear()


def test_registry_registration(reset_registry):
    portfolio_adapter_registry.register("fyers", FyersPortfolioAdapter())
    assert "fyers" in portfolio_adapter_registry.list_adapters()


def test_registry_lookup(reset_registry):
    portfolio_adapter_registry.register("groww", GrowwPortfolioAdapter())
    adapter = portfolio_adapter_registry.get("groww")
    assert adapter is not None


def test_registry_unsupported(reset_registry):
    with pytest.raises(ValueError):
        portfolio_adapter_registry.get("ghost")


def test_fyers_positions_translation():
    adapter = FyersPortfolioAdapter()

    raw = [
        {
            "symbol": "NSE:SBIN-EQ",
            "qty": 10,
            "avg_price": 820.0,
            "ltp": 830.0,
            "side": "BUY",
            "productType": "CNC",
        }
    ]

    out = adapter.translate_positions(raw)

    assert len(out) == 1
    assert out[0].symbol == "NSE:SBIN-EQ"


def test_groww_positions_translation():
    adapter = GrowwPortfolioAdapter()

    raw = [
        {
            "instrument": "NSE:TCS-EQ",
            "quantity": 5,
            "avg_price": 3500.0,
            "ltp": 3550.0,
        }
    ]

    out = adapter.translate_positions(raw)

    assert len(out) == 1
    assert out[0].symbol == "NSE:TCS-EQ"


def test_viewtrade_positions_translation():
    adapter = ViewTradePortfolioAdapter()

    raw = [
        {
            "ticker": "AAPL",
            "quantity": 3,
            "avg_price": 190.0,
            "market_price": 195.0,
        }
    ]

    out = adapter.translate_positions(raw)

    assert len(out) == 1
    assert out[0].symbol == "AAPL"


def test_coinswitch_positions_translation():
    adapter = CoinSwitchPortfolioAdapter()

    raw = [
        {
            "symbol": "BTC-INR",
            "quantity": 1,
            "avg_price": 5000000,
            "ltp": 5100000,
        }
    ]

    out = adapter.translate_positions(raw)

    assert len(out) == 1
    assert out[0].symbol == "BTC-INR"


def test_balance_model():
    bal = CanonicalBalance(
        provider="fyers",
        cash=1000,
        margin_available=500,
        margin_used=200,
        collateral=100,
    )

    assert bal.cash == 1000


def test_margin_model():
    m = CanonicalMarginSnapshot(
        provider="fyers",
        available=1000,
        used=200,
        collateral=100,
        leverage=5,
    )

    assert m.leverage == 5


def test_exposure_model():
    ex = CanonicalExposureSnapshot(
        provider="fyers",
        portfolio_exposure_pct=45.0,
    )

    assert ex.portfolio_exposure_pct == 45.0


def test_risk_model():
    risk = CanonicalRiskSnapshot(
        provider="fyers",
        drawdown_pct=4.5,
        realized_pnl=100,
    )

    assert risk.drawdown_pct == 4.5


def test_portfolio_snapshot():
    snap = CanonicalPortfolioSnapshot(
        provider="fyers",
        positions=[],
        balance=CanonicalBalance(provider="fyers"),
    )

    assert snap.provider == "fyers"