class PortfolioBrain:

    def __init__(self, capital=100000):
        self.capital = capital
        self.max_risk_per_trade = 0.02
        self.max_positions = 5

    def calculate_position_size(self, entry, stop_loss):
        risk_per_unit = abs(entry - stop_loss)

        if risk_per_unit == 0:
            return 0

        risk_capital = self.capital * self.max_risk_per_trade

        qty = risk_capital / risk_per_unit

        return int(qty)

    def can_take_trade(self, positions, symbol):
        # avoid duplicate
        if symbol in positions:
            return False

        # max positions
        if len(positions) >= self.max_positions:
            return False

        return True