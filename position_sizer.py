# position_sizer.py

class PositionSizer:

    def __init__(self, capital=100000, risk_per_trade=0.01):
        self.capital = capital
        self.risk_per_trade = risk_per_trade

    def size(self, price, stop_loss):
        risk_amount = self.capital * self.risk_per_trade
        risk_per_unit = abs(price - stop_loss)

        if risk_per_unit == 0:
            return 0

        qty = int(risk_amount / risk_per_unit)

        return max(qty, 1)