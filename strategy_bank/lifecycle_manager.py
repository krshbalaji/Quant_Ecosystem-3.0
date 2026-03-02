class StrategyLifecycleManager:

    def promote(self, report):
        winrate = report["win_rate"]
        expectancy = report["expectancy"]

        if winrate > 60 and expectancy > 0.2:
            return "LIVE"

        if winrate > 55 and expectancy > 0:
            return "PAPER"

        return "REJECTED"
