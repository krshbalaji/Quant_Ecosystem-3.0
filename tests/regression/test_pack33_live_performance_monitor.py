from quant_ecosystem.monitoring.live_performance_monitor import (
    live_performance_monitor,
)


def test_strategy_snapshot():
    result = (
        live_performance_monitor
        .strategy_snapshot(
            "alpha_1",
            realized_pnl=1000,
            unrealized_pnl=500,
            exposure=20000,
        )
    )

    assert result["health"] == "HEALTHY"


def test_portfolio_snapshot():
    snapshots = [
        {
            "realized_pnl": 100,
            "unrealized_pnl": 50,
            "exposure": 10000,
        },
        {
            "realized_pnl": -20,
            "unrealized_pnl": 10,
            "exposure": 5000,
        },
    ]

    result = (
        live_performance_monitor
        .portfolio_snapshot(
            snapshots
        )
    )

    assert result["strategy_count"] == 2
    assert result["total_exposure"] == 15000