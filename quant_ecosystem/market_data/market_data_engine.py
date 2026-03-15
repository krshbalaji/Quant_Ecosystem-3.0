import logging
from typing import List, Dict
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataEngine:

    def __init__(self):
        self.cache = {}

    def get_candles(self, symbol: str, timeframe="1d", lookback=400) -> List[Dict]:

        try:
            df = yf.download(
                symbol,
                period="2y",
                interval=timeframe,
                progress=False
            )

            candles = []

            for idx, row in df.iterrows():
                candles.append({
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                    "ts": str(idx)
                })

            logger.info(f"MarketDataEngine loaded {len(candles)} candles for {symbol}")

            return candles[-lookback:]

        except Exception as e:
            logger.warning(f"MarketDataEngine failed → {symbol} → {e}")
            return []