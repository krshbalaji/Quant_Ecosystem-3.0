from quant_ecosystem.research.research_backtest_harness import (
    research_backtest_harness,
)


SIGNALS = [
    {
        "symbol": "SBIN",
        "direction": "LONG",
        "entry_price": 100,
        "exit_price": 110,
    },
    {
        "symbol": "INFY",
        "direction": "SHORT",
        "entry_price": 200,
        "exit_price": 180,
    },
    {
        "symbol": "TCS",
        "direction": "LONG",
        "entry_price": 300,
        "exit_price": 280,
    },
]


def test_replay():
    result = (
        research_backtest_harness
        .replay(SIGNALS)
    )

    assert len(result) == 3
    assert result[0]["pnl"] == 10
    assert result[1]["pnl"] == 20


def test_snapshot():
    replay = (
        research_backtest_harness
        .replay(SIGNALS)
    )

    snapshot = (
        research_backtest_harness
        .performance_snapshot(
            replay
        )
    )

    assert snapshot["trades"] == 3
    assert snapshot["wins"] == 2
    assert snapshot["losses"] == 1


def test_run():
    result = (
        research_backtest_harness
        .run(SIGNALS)
    )

    assert "snapshot" in result
    assert result["snapshot"]["total_pnl"] == 10