from quant_ecosystem.strategy_execution import (
    strategy_execution_context,
    strategy_attribution_bridge,
)


def setup_function():
    strategy_execution_context.clear()
    strategy_attribution_bridge.clear()


def test_record_fill_win():
    strategy_execution_context.attach(
        order_id="ORD1",
        strategy_id="alpha",
    )

    bucket = strategy_attribution_bridge.record_fill(
        "ORD1",
        pnl=1000,
    )

    assert bucket["realized_pnl"] == 1000
    assert bucket["wins"] == 1


def test_record_fill_loss():
    strategy_execution_context.attach(
        order_id="ORD2",
        strategy_id="alpha",
    )

    bucket = strategy_attribution_bridge.record_fill(
        "ORD2",
        pnl=-500,
    )

    assert bucket["losses"] == 1


def test_unrealized_mark():
    strategy_attribution_bridge.mark_unrealized(
        "alpha",
        250,
    )

    summary = strategy_attribution_bridge.summary(
        "alpha"
    )

    assert summary["unrealized_pnl"] == 250


def test_summary_win_rate():
    strategy_execution_context.attach(
        order_id="A",
        strategy_id="alpha",
    )

    strategy_execution_context.attach(
        order_id="B",
        strategy_id="alpha",
    )

    strategy_attribution_bridge.record_fill(
        "A",
        pnl=100,
    )

    strategy_attribution_bridge.record_fill(
        "B",
        pnl=-50,
    )

    summary = strategy_attribution_bridge.summary(
        "alpha"
    )

    assert summary["trade_count"] == 2
    assert summary["win_rate"] == 50.0


def test_missing_context_returns_none():
    result = strategy_attribution_bridge.record_fill(
        "UNKNOWN",
        pnl=100,
    )

    assert result is None