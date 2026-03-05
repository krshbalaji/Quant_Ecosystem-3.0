import yfinance as yf


class YahooFeed:

    name = "yahoo"

    def fetch(self, symbol, timeframe):

        try:

            data = yf.download(symbol, period="1d", interval="5m")

            if data is None or data.empty:
                return None

            return data

        except Exception:

            return None