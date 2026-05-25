from quant_ecosystem.backtest.backtest_engine import (
    backtest_engine,
)


TRADES = [
    {
        "entry": {
            "symbol": "SBIN",
            "side": "BUY",
            "qty": 10,
            "price": 100,
        },
        "exit": {
            "symbol": "SBIN",
            "price": 110,
        },
    },
    {
        "entry": {
            "symbol": "INFY",
            "side": "SELL",
            "qty": 5,
            "price": 200,
        },
        "exit": {
            "symbol": "INFY",
            "price": 180,
        },
    },
]


def test_fill_simulation():
    fill = (
        backtest_engine
        .simulate_fill(
            TRADES[0]["entry"]
        )
    )

    assert fill["fill_price"] == 100.0


def test_trade_pnl():
    fill = (
        backtest_engine
        .simulate_fill(
            TRADES[0]["entry"]
        )
    )

    pnl = (
        backtest_engine
        .pnl_for_trade(
            fill,
            TRADES[0]["exit"],
        )
    )

    assert pnl == 100


def test_equity_curve():
    curve = (
        backtest_engine
        .equity_curve(
            [100, 50],
            starting_equity=1000,
        )
    )

    assert curve == [
        1000,
        1100,
        1150,
    ]


def test_run():
    result = (
        backtest_engine
        .run(TRADES)
    )

    assert result["wins"] == 2
    assert result["total_pnl"] == 200