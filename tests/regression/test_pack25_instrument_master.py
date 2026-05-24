import pytest

from quant_ecosystem.portfolio.portfolio_engine import PortfolioEngine
from quant_ecosystem.risk.risk_engine import RiskEngine
from quant_ecosystem.accounting import (
    CanonicalTradeFill,
    accounting_engine,
)


@pytest.fixture
def reset_accounting():
    accounting_engine.clear()
    yield
    accounting_engine.clear()


def test_equity_portfolio_fill():
    pe = PortfolioEngine()

    pe.apply_fill(
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
        price=100.0,
    )

    snap = pe.snapshot()

    assert "NSE:SBIN-EQ" in snap
    assert snap["NSE:SBIN-EQ"]["net_qty"] == 10
    assert snap["NSE:SBIN-EQ"]["multiplier"] == 1.0
    assert snap["NSE:SBIN-EQ"]["asset_class"] == "EQUITY"


def test_derivative_portfolio_multiplier():
    pe = PortfolioEngine()

    pe.apply_fill(
        symbol="NIFTY25JUN24500CE",
        side="BUY",
        qty=75,
        price=100.0,
        multiplier=1.0,
        asset_class="OPTIONS",
    )

    mv = pe.market_value(
        {
            "NIFTY25JUN24500CE": 120.0
        }
    )

    assert mv == 9000.0


def test_derivative_realized_pnl():
    pe = PortfolioEngine()

    pe.apply_fill(
        symbol="NIFTY25JUN24500CE",
        side="BUY",
        qty=75,
        price=100.0,
        multiplier=1.0,
        asset_class="OPTIONS",
    )

    result = pe.apply_fill(
        symbol="NIFTY25JUN24500CE",
        side="SELL",
        qty=75,
        price=120.0,
        multiplier=1.0,
        asset_class="OPTIONS",
    )

    assert result["realized_pnl"] == 1500.0


def test_asset_bucket_exposure():
    pe = PortfolioEngine()

    pe.apply_fill(
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
        price=100.0,
        asset_class="EQUITY",
    )

    pe.apply_fill(
        symbol="NIFTY25JUN24500CE",
        side="BUY",
        qty=75,
        price=100.0,
        asset_class="OPTIONS",
    )

    eq = pe.asset_exposure_notional(
        "EQUITY",
        {
            "NSE:SBIN-EQ": 100.0,
            "NIFTY25JUN24500CE": 100.0,
        },
    )

    opt = pe.asset_exposure_notional(
        "OPTIONS",
        {
            "NSE:SBIN-EQ": 100.0,
            "NIFTY25JUN24500CE": 100.0,
        },
    )

    assert eq == 1000.0
    assert opt == 7500.0


def test_risk_derivative_lot_validation():
    re = RiskEngine()

    allowed, reason = re.check_order(
        {
            "symbol": "NIFTY25JUN24500CE",
            "side": "BUY",
            "qty": 10,
            "price": 100.0,
        }
    )

    assert allowed is False
    assert reason == "INVALID_DERIVATIVE_QTY"


def test_risk_equity_valid():
    re = RiskEngine()

    allowed, reason = re.check_order(
        {
            "symbol": "NSE:SBIN-EQ",
            "side": "BUY",
            "qty": 10,
            "price": 100.0,
        }
    )

    assert allowed is True


def test_accounting_equity_unchanged(reset_accounting):
    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=10,
            price=100.0,
        )
    )

    assert snap.fills_processed == 1


def test_accounting_derivative_fill(reset_accounting):
    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NIFTY25JUN24500CE",
            side="BUY",
            qty=75,
            price=100.0,
        )
    )

    assert snap.fills_processed == 1


def test_accounting_derivative_mtm(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NIFTY25JUN24500CE",
            side="BUY",
            qty=75,
            price=100.0,
        )
    )

    snap = accounting_engine.mark_to_market(
        "NIFTY25JUN24500CE",
        120.0,
    )

    assert snap.unrealized_pnl > 0