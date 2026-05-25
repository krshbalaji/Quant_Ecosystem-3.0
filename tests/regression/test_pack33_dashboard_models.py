from quant_ecosystem.monitoring.dashboard_models import (
    dashboard_models,
)


def test_cio_snapshot():
    result = (
        dashboard_models
        .cio_snapshot(
            total_pnl=10000,
            total_exposure=500000,
            drawdown=15000,
            active_strategies=8,
        )
    )

    assert result["role"] == "CIO"


def test_pm_snapshot():
    result = (
        dashboard_models
        .pm_snapshot(
            strategy_id="alpha_1",
            pnl=2000,
            exposure=100000,
            health="HEALTHY",
        )
    )

    assert result["role"] == "PM"


def test_heatmap():
    result = (
        dashboard_models
        .strategy_heatmap(
            [
                {
                    "strategy_id": "s1",
                    "health": "WATCH",
                    "pnl": 100,
                }
            ]
        )
    )

    assert len(result) == 1


def test_risk_command():
    result = (
        dashboard_models
        .risk_command_center(
            anomalies=2,
            alerts=1,
            guardian_action="WATCH",
        )
    )

    assert result["guardian_action"] == (
        "WATCH"
    )