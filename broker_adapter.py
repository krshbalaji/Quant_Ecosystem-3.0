class BrokerAdapter:

    def __init__(self, mode="paper"):
        self.mode = mode

    def place_order(self, symbol, side, qty):
        if self.mode == "paper":
            print(f"[BROKER PAPER] {side} {qty} {symbol}")
            return {"status": "simulated"}

        # --- future: real API here
        print(f"[BROKER LIVE] {side} {qty} {symbol}")
        return {"status": "live"}