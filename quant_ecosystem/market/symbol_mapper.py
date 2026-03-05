import re


class SymbolMapper:

    def __init__(self):

        self.index_map = {
            "NIFTY50": {
                "fyers": "NSE:NIFTY50-INDEX",
                "nse": "NIFTY 50",
                "tradingview": "NIFTY",
                "yahoo": "^NSEI"
            },
            "BANKNIFTY": {
                "fyers": "NSE:BANKNIFTY-INDEX",
                "nse": "NIFTY BANK",
                "tradingview": "BANKNIFTY",
                "yahoo": "^NSEBANK"
            }
        }

    # ----------------------------------------------------

    def to_fyers(self, symbol):

        if symbol in self.index_map:
            return self.index_map[symbol]["fyers"]

        return f"NSE:{symbol}-EQ"

    # ----------------------------------------------------

    def to_nse(self, symbol):

        if symbol in self.index_map:
            return self.index_map[symbol]["nse"]

        return symbol

    # ----------------------------------------------------

    def to_tradingview(self, symbol):

        if symbol in self.index_map:
            return self.index_map[symbol]["tradingview"]

        return symbol

    # ----------------------------------------------------

    def to_yahoo(self, symbol):

        if symbol in self.index_map:
            return self.index_map[symbol]["yahoo"]

        return f"{symbol}.NS"

    # ----------------------------------------------------

    def map(self, symbol, provider):

        provider = provider.lower()

        if provider == "fyers":
            return self.to_fyers(symbol)

        if provider == "nse":
            return self.to_nse(symbol)

        if provider == "tradingview":
            return self.to_tradingview(symbol)

        if provider == "yahoo":
            return self.to_yahoo(symbol)

        return symbol