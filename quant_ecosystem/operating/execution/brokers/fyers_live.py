class FyersLiveBroker:

    def place_order(self, symbol, side, qty):

        print(f"📡 LIVE ORDER → {symbol} {side} x {qty}")

        # Replace with actual fyers API later
        return {
            "status": "placed",
            "symbol": symbol,
            "qty": qty
        }