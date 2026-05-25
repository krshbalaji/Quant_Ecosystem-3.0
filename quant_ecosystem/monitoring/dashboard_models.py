class DashboardModels:

    def cio_snapshot(
        self,
        total_pnl,
        total_exposure,
        drawdown,
        active_strategies,
    ):
        return {
            "role": "CIO",
            "total_pnl": total_pnl,
            "total_exposure": total_exposure,
            "drawdown": drawdown,
            "active_strategies": (
                active_strategies
            ),
        }

    def pm_snapshot(
        self,
        strategy_id,
        pnl,
        exposure,
        health,
    ):
        return {
            "role": "PM",
            "strategy_id": strategy_id,
            "pnl": pnl,
            "exposure": exposure,
            "health": health,
        }

    def strategy_heatmap(
        self,
        snapshots,
    ):
        return [
            {
                "strategy_id": (
                    x["strategy_id"]
                ),
                "health": x["health"],
                "pnl": x["pnl"],
            }
            for x in snapshots
        ]

    def risk_command_center(
        self,
        anomalies,
        alerts,
        guardian_action,
    ):
        return {
            "anomalies": anomalies,
            "alerts": alerts,
            "guardian_action": (
                guardian_action
            ),
        }


dashboard_models = DashboardModels()