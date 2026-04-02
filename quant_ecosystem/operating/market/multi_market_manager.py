class MultiMarketManager:

    def get_universe(self):

        return {
            "NSE": ["NIFTY", "BANKNIFTY", "RELIANCE"],
            "CRYPTO": ["BTCUSDT", "ETHUSDT"]
        }