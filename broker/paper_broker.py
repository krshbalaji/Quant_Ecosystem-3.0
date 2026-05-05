class PaperBroker:

    def place_order(self, symbol, side, qty):
        print(f"[BROKER PAPER] {side} {qty} {symbol}")
        return {
            "success": True,
            "symbol": symbol,
            "side": side,
            "qty": qty
        }


# singleton instance
broker = PaperBroker()