class StrategyLifecycleManager:

    STAGES = ("candidate", "paper", "shadow", "live", "retired")

    def assess(self, metrics, current_stage="candidate"):
        win_rate = float(metrics.get("win_rate", 0.0))
        profit_factor = float(metrics.get("profit_factor", 0.0))
        sharpe = float(metrics.get("sharpe", 0.0))
        drawdown = float(metrics.get("max_dd", 100.0))
        sample_size = int(metrics.get("sample_size", metrics.get("returns_count", 200)))
        expectancy_rolling = float(metrics.get("expectancy_rolling_100", metrics.get("expectancy", 0.0)))

        if drawdown >= 20.0:
            return "retired"

        if (
            sample_size >= 120
            and 45.0 <= win_rate <= 60.0
            and profit_factor >= 1.5
            and sharpe >= 1.8
            and drawdown < 15.0
            and expectancy_rolling > 0
        ):
            return "live"

        if (
            sample_size >= 60
            and profit_factor >= 1.1
            and sharpe >= 0.5
            and drawdown < 18.0
            and expectancy_rolling >= 0
        ):
            return "paper"

        if (
            sample_size >= 20
            and profit_factor >= 1.0
            and drawdown < 20.0
        ):
            return "shadow"

        if current_stage == "retired":
            return "retired"
        return "candidate"
