import logging
from typing import List, Dict
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataEngine:

    def __init__(self):
        self.cache = {}

    def get_candles(self, symbol: str, timeframe="1d", lookback=400):
        
        print("📡 REQUEST →", symbol, timeframe, lookback)

        try:
            if timeframe in ["1m", "5m", "15m"]:
                period = "60d"
            elif timeframe in ["30m", "60m", "1h"]:
                period = "730d"
            else:
                period = "max"

            df = yf.download(
                symbol,
                period=period,
                interval=timeframe,
                progress=False
            )

            candles = []
            candles = candles[-min(len(candles), lookback):]
                
            for idx, row in df.iterrows():
                candles.append({
                    "open": float(row["Open"].iloc[0] if hasattr(row["Open"], "iloc") else row["Open"]),
                    "high": float(row["High"].iloc[0] if hasattr(row["High"], "iloc") else row["High"]),
                    "low": float(row["Low"].iloc[0] if hasattr(row["Low"], "iloc") else row["Low"]),
                    "close": float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]),
                    "volume": float(row["Volume"].iloc[0] if hasattr(row["Volume"], "iloc") else row["Volume"]),
                    "ts": str(idx)
                })

            print("📡 RECEIVED →", len(candles))

            logger.info(f"MarketDataEngine loaded {len(candles)} candles for {symbol}")

            return candles[-lookback:]

        except Exception as e:
            logger.warning(f"MarketDataEngine failed → {symbol} → {e}")
            return []