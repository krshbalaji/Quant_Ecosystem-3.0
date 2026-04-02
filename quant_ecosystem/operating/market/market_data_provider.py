class MarketDataProvider:
    async def get_price(self, symbol):
        raise NotImplementedError

    async def get_ohlc(self, symbol, timeframe):
        raise NotImplementedError

    async def get_volume(self, symbol):
        raise NotImplementedError