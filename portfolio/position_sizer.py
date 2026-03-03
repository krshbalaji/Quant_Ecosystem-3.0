from core.config_loader import Config


class PositionSizer:

    def __init__(self):
        self.config = Config()

    def size(self, equity, price, volatility, risk_pct=1.0):
        if equity <= 0 or price <= 0:
            return 0

        vol = max(float(volatility), self.config.sizer_min_volatility)
        risk_per_trade = float(equity) * (max(float(risk_pct), 0.1) / 100.0)
        raw_position = risk_per_trade / (float(price) * vol)

        max_notional = float(equity) * (self.config.sizer_max_notional_pct / 100.0)
        max_qty = int(max_notional / float(price))
        sized_qty = int(raw_position)

        if max_qty <= 0:
            return 0
        return max(0, min(sized_qty, max_qty))
