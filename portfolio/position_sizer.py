class PositionSizer:

    def size(self, equity, price, volatility):

        risk_per_trade = equity * 0.01

        position = risk_per_trade / (price * volatility)

        return int(position)
