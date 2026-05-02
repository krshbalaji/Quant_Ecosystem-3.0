# quant_ecosystem/broker/paper_broker.py

class PaperBroker:

    def __init__(self):
        self.positions = {}
        self.orders = []

    def place_order(self, symbol, side, qty, **kwargs):

        print(f"🧪 PAPER ORDER: {side} {symbol} x{qty}")

        if side == "BUY":
            self.positions[symbol] = self.positions.get(symbol, 0) + qty
        elif side == "SELL":
            self.positions[symbol] = self.positions.get(symbol, 0) - qty

        self.orders.append({
            "symbol": symbol,
            "side": side,
            "qty": qty
        })

        return {"status": "filled"}

    def close_position(self, symbol):
        if symbol in self.positions:
            print(f"🧪 CLOSE {symbol}")
            self.positions[symbol] = 0

    def get_positions(self):
        return self.positions

    def get_orders(self):
        return self.orders

    def get_balance(self):
        return {"balance": 100000}

    def get_account_snapshot(self, latest_prices=None):
        return {
            "positions": self.positions,
            "orders": self.orders
        }