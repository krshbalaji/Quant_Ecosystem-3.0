class Broker:

    def __init__(self, mode="paper"):
        self.mode = mode

    def place_order(self, symbol, side, qty):
        if self.mode == "paper":
            print(f"[BROKER PAPER] {side} {qty} {symbol}")
        else:
            # 🔥 plug real broker API here
            print(f"[LIVE BROKER] {side} {qty} {symbol}")