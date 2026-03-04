import numpy as np
import time


class CapitalIntelligenceEngine:

    def __init__(
        self,
        portfolio_engine,
        risk_engine,
        base_risk=0.02,
        max_risk=0.05,
        min_risk=0.005,
        evaluation_interval=120,
    ):

        self.portfolio = portfolio_engine
        self.risk = risk_engine

        self.base_risk = base_risk
        self.max_risk = max_risk
        self.min_risk = min_risk

        self.interval = evaluation_interval
        self.last_run = 0

        self.current_risk = base_risk

    def start(self):

        print("Capital Intelligence Engine started.")

    def evaluate(self):

        now = time.time()

        if now - self.last_run < self.interval:
            return

        self.last_run = now

        stats = self.portfolio.get_portfolio_stats()

        sharpe = stats.get("sharpe", 0)
        drawdown = stats.get("drawdown", 0)
        win_rate = stats.get("win_rate", 0)

        new_risk = self._calculate_risk(sharpe, drawdown, win_rate)

        self.current_risk = new_risk

        self.risk.set_trade_risk(new_risk)

        print(
            "Capital Intelligence:",
            {
                "sharpe": sharpe,
                "drawdown": drawdown,
                "win_rate": win_rate,
                "risk": new_risk,
            },
        )

    def _calculate_risk(self, sharpe, drawdown, win_rate):

        score = (
            sharpe * 0.5
            + (win_rate / 100) * 0.3
            - drawdown * 0.2
        )

        score = max(-1, min(score, 2))

        risk = self.base_risk * (1 + score)

        risk = max(self.min_risk, min(self.max_risk, risk))

        return risk