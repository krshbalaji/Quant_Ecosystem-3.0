class LivePerformanceMonitor:

    def strategy_snapshot(
        self,
        strategy_id,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        exposure=0.0,
    ):
        total = (
            realized_pnl
            + unrealized_pnl
        )

        if total > 0:
            health = "HEALTHY"
        elif total > -5000:
            health = "WATCH"
        else:
            health = "CRITICAL"

        return {
            "strategy_id": strategy_id,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total,
            "exposure": exposure,
            "health": health,
        }

    def portfolio_snapshot(
        self,
        strategy_snapshots,
    ):
        total_realized = sum(
            x["realized_pnl"]
            for x in strategy_snapshots
        )

        total_unrealized = sum(
            x["unrealized_pnl"]
            for x in strategy_snapshots
        )

        total_exposure = sum(
            x["exposure"]
            for x in strategy_snapshots
        )

        total = (
            total_realized
            + total_unrealized
        )

        return {
            "strategy_count": len(
                strategy_snapshots
            ),
            "total_realized": total_realized,
            "total_unrealized": total_unrealized,
            "total_pnl": total,
            "total_exposure": total_exposure,
        }


live_performance_monitor = (
    LivePerformanceMonitor()
)