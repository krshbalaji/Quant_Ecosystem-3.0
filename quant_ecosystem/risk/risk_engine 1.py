class RiskEngine:

    def __init__(self):

        self.max_daily_drawdown = 5
        self.max_trade_risk = 1
        self.max_portfolio_risk = 10

    def check_trade(self, state):

        if state.daily_drawdown > self.max_daily_drawdown:
            return False, "Daily drawdown limit hit"

        if state.open_risk > self.max_portfolio_risk:
            return False, "Portfolio risk exceeded"

        return True, "Allowed"

    def trade_risk(self, equity):

        return equity * (self.max_trade_risk / 100)