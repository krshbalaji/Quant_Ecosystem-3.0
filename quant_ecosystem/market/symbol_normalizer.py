class SymbolNormalizer:
    """
    Normalize symbols into broker-safe canonical forms.
    """

    NSE_EQ_SUFFIX = "-EQ"

    INDIA_EQ_MAP = {
        "SBIN": "NSE:SBIN-EQ",
        "ITC": "NSE:ITC-EQ",
        "RELIANCE": "NSE:RELIANCE-EQ",
        "TCS": "NSE:TCS-EQ",
        "INFY": "NSE:INFY-EQ",
    }

    def normalize(self, symbol: str, market: str, asset_class: str):
        symbol = (symbol or "").strip().upper()
        market = (market or "").upper()
        asset_class = (asset_class or "").upper()

        if not symbol:
            raise RuntimeError("Symbol required")

        if market == "INDIA":
            return self._normalize_india(symbol, asset_class)

        if market == "US":
            return symbol

        if market == "CRYPTO":
            return self._normalize_crypto(symbol)

        if market == "GLOBAL":
            return symbol

        raise RuntimeError(f"Unsupported market: {market}")

    def _normalize_india(self, symbol, asset_class):
        if symbol.startswith("NSE:"):
            return symbol

        if asset_class == "EQUITY":
            if symbol in self.INDIA_EQ_MAP:
                return self.INDIA_EQ_MAP[symbol]

            return f"NSE:{symbol}{self.NSE_EQ_SUFFIX}"

        return symbol

    def _normalize_crypto(self, symbol):
        if "/" in symbol:
            return symbol

        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT"

        return symbol