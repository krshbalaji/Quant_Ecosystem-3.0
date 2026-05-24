from quant_ecosystem.strategy import (
    attribution_engine,
)


def test_strategy_pnl():
    trades = [
        {"pnl": 100},
        {"pnl": -50},
    ]

    assert (
        attribution_engine.strategy_pnl(trades)
        == 50
    )


def test_win_rate():
    trades = [
        {"pnl": 100},
        {"pnl": -50},
        {"pnl": 25},
    ]

    wr = attribution_engine.win_rate(trades)

    assert wr > 60


def test_expectancy():
    trades = [
        {"pnl": 100},
        {"pnl": -50},
    ]

    exp = attribution_engine.expectancy(trades)

    assert exp != 0


def test_max_drawdown():
    eq = [
        100000,
        105000,
        102000,
        95000,
        98000,
    ]

    dd = attribution_engine.max_drawdown(eq)

    assert dd > 0


def test_sharpe_proxy():
    s = attribution_engine.sharpe_proxy(
        [0.01, 0.02, -0.01]
    )

    assert s != 0


def test_summary():
    trades = [
        {"pnl": 100},
        {"pnl": -20},
        {"pnl": 50},
    ]

    summary = attribution_engine.strategy_summary(
        trades=trades,
        equity_curve=[100, 110, 95],
        returns=[0.1, -0.05],
        total_system_pnl=500,
    )

    assert "pnl" in summary
    assert "win_rate" in summary
    assert "contribution_pct" in summary