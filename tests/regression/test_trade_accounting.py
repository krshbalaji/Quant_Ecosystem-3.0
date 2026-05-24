import pytest

from quant_ecosystem.accounting import (
    AccountingMethod,
    CanonicalTradeFill,
    accounting_engine,
)


@pytest.fixture
def reset_accounting():
    accounting_engine.clear()
    yield
    accounting_engine.clear()


def test_buy_creates_lot(reset_accounting):
    fill = CanonicalTradeFill(
        broker="fyers",
        symbol="NSE:SBIN-EQ",
        side="BUY",
        qty=10,
        price=100.0,
    )

    snap = accounting_engine.process_fill(fill)

    assert len(snap.open_lots) == 1
    assert snap.open_lots[0].qty == 10


def test_fifo_realized_pnl(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=10,
            price=100.0,
        )
    )

    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="SELL",
            qty=10,
            price=110.0,
        ),
        method=AccountingMethod.FIFO,
    )

    assert snap.realized_pnl == 100.0


def test_lifo_realized_pnl(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=5,
            price=100.0,
        )
    )

    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="BUY",
            qty=5,
            price=120.0,
        )
    )

    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:SBIN-EQ",
            side="SELL",
            qty=5,
            price=130.0,
        ),
        method=AccountingMethod.LIFO,
    )

    assert snap.realized_pnl == 50.0


def test_partial_sell(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:TCS-EQ",
            side="BUY",
            qty=10,
            price=200.0,
        )
    )

    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="NSE:TCS-EQ",
            side="SELL",
            qty=4,
            price=220.0,
        )
    )

    assert snap.realized_pnl == 80.0
    assert len(snap.open_lots) == 1
    assert snap.open_lots[0].qty == 6


def test_sell_exceeds_inventory(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="AAPL",
            side="BUY",
            qty=2,
            price=100.0,
        )
    )

    with pytest.raises(ValueError):
        accounting_engine.process_fill(
            CanonicalTradeFill(
                broker="fyers",
                symbol="AAPL",
                side="SELL",
                qty=5,
                price=120.0,
            )
        )


def test_unrealized_pnl(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="BTC-INR",
            side="BUY",
            qty=1,
            price=5000000,
        )
    )

    snap = accounting_engine.mark_to_market(
        "BTC-INR",
        5200000,
    )

    assert snap.unrealized_pnl == 200000


def test_weighted_avg_entry(reset_accounting):
    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="INFY",
            side="BUY",
            qty=10,
            price=100.0,
        )
    )

    accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="INFY",
            side="BUY",
            qty=10,
            price=200.0,
        )
    )

    avg = accounting_engine.weighted_avg_entry("INFY")

    assert avg == 150.0


def test_fee_application(reset_accounting):
    snap = accounting_engine.process_fill(
        CanonicalTradeFill(
            broker="fyers",
            symbol="HDFCBANK",
            side="BUY",
            qty=10,
            price=100.0,
            fees=25.0,
            slippage=10.0,
        )
    )

    assert snap.total_fees == 25.0
    assert snap.total_slippage == 10.0


def test_duplicate_fill_ignored(reset_accounting):
    fill = CanonicalTradeFill(
        broker="fyers",
        symbol="ICICIBANK",
        side="BUY",
        qty=10,
        price=100.0,
    )

    accounting_engine.process_fill(fill)
    snap = accounting_engine.process_fill(fill)

    assert snap.fills_processed == 1


def test_invalid_qty():
    with pytest.raises(ValueError):
        CanonicalTradeFill(
            broker="fyers",
            symbol="RELIANCE",
            side="BUY",
            qty=0,
            price=100.0,
        )