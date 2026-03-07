from quant_ecosystem.core.config_loader import Config


class StrategyLifecycleManager:

    def __init__(self, **kwargs):
        self.config = Config()

    def promote(self, report):
        winrate = float(report.get("win_rate", 0.0))
        expectancy = float(report.get("expectancy", 0.0))
        expectancy_rolling = float(report.get("expectancy_rolling_100", expectancy))
        max_dd = float(report.get("max_dd", 99.0))
        profit_factor = float(report.get("profit_factor", 0.0))
        sharpe = float(report.get("sharpe", 0.0))

        if (
            45.0 <= winrate <= 60.0
            and expectancy_rolling > 0
            and profit_factor >= self.config.live_min_profit_factor
            and sharpe >= self.config.live_min_sharpe
            and max_dd < 15.0
        ):
            return "LIVE"

        if (
            expectancy_rolling >= 0
            and expectancy >= 0
            and profit_factor >= self.config.paper_min_profit_factor
            and sharpe >= self.config.paper_min_sharpe
            and max_dd < 15.0
        ):
            return "PAPER"

        return "REJECTED"
