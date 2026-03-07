class DataSourceRouter:

    def __init__(self, primary_feed, **kwargs):

        self.primary = primary_feed

    def fetch(self, symbol, timeframe):

        try:
            data = self.primary.fetch(symbol, timeframe)

            if data is not None:
                return data

        except Exception:
            pass

        return None