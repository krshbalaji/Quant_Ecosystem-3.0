import logging
from typing import Any, Dict, List, cast

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataEngine:

    def __init__(self):
        self.cache = {}

    def get_candles(
        self,
        symbol: str,
        timeframe="1d",
        lookback=400,
    ) -> List[Dict]:

        try:
            df = yf.download(
                symbol,
                period="2y",
                interval=timeframe,
                progress=False,
            )

            if df is None or df.empty:
                return []

            candles: List[Dict[str, Any]] = []

            for idx, row in cast(pd.DataFrame, df).iterrows():

                open_price = float(row.get("Open", 0.0) or 0.0)
                high_price = float(row.get("High", 0.0) or 0.0)
                low_price = float(row.get("Low", 0.0) or 0.0)
                close_price = float(row.get("Close", 0.0) or 0.0)
                volume = float(row.get("Volume", 0.0) or 0.0)

                candles.append(
                    {
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                        "ts": str(idx),
                    }
                )

            logger.info(
                f"MarketDataEngine loaded {len(candles)} candles for {symbol}"
            )

            return candles[-lookback:]

        except Exception as e:
            logger.warning(
                f"MarketDataEngine failed → {symbol} → {e}"
            )
            return []