import pandas as pd
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
                interval=timeframe,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False,
            )

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df = df.dropna()

            if df is None or len(df) == 0:
                raise RuntimeError(f"Yahoo returned empty dataframe for {symbol}")

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

            candles = candles[-lookback:]

            print("📡 RECEIVED →", len(candles))

            logger.info(f"MarketDataEngine loaded {len(candles)} candles for {symbol}")

            return candles

        except Exception as e:
            logger.warning(f"MarketDataEngine failed → {symbol} → {e}")
            return []