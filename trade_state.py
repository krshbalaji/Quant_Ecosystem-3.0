import time
ACTIVE_TRADES = {}

class TradeState:
    def __init__(self, cooldown=120):
        self.last_trade_time = {}
        self.cooldown = cooldown  # seconds

    def can_trade(self, symbol):
        now = time.time()

        if symbol not in self.last_trade_time:
            return True

        if now - self.last_trade_time[symbol] > self.cooldown:
            return True

        return False

    def record_trade(self, symbol):
        self.last_trade_time[symbol] = time.time()