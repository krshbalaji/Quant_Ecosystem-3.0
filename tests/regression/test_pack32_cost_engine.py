from quant_ecosystem.backtest.cost_engine import (
    cost_engine,
)


def test_buy_slippage():
    result = (
        cost_engine
        .apply_slippage(
            100,
            "BUY",
        )
    )

    assert result > 100


def test_sell_slippage():
    result = (
        cost_engine
        .apply_slippage(
            100,
            "SELL",
        )
    )

    assert result < 100


def test_commission():
    result = (
        cost_engine
        .commission(
            100000
        )
    )

    assert result > 0


def test_net_trade_pnl():
    result = (
        cost_engine
        .net_trade_pnl(
            entry_price=100,
            exit_price=110,
            qty=10,
            side="BUY",
        )
    )

    assert result["gross_pnl"] > 0
    assert result["fees"] > 0
    assert (
        result["net_pnl"]
        < result["gross_pnl"]
    )