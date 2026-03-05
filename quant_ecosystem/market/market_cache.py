from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional


class MarketCache:
    """
    Rolling in-memory cache of OHLCV candles.

    Internally stores a deque per (symbol, timeframe) pair, but exposes
    a simple API that defaults to the primary timeframe when not given.
    """

    def __init__(self, history: int = 500):
        self._history = int(history)
        self._cache: Dict[str, Dict[str, Deque[dict]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=self._history))
        )

    def update(self, symbol: str, candle: dict, timeframe: str = "5m") -> None:
        self._cache[str(symbol)][str(timeframe)].append(candle)

    def get_series(self, symbol: str, timeframe: str = "5m", lookback: Optional[int] = None) -> List[dict]:
        rows = list(self._cache.get(str(symbol), {}).get(str(timeframe), []))
        if lookback is not None and lookback > 0:
            rows = rows[-lookback:]
        return rows

    def get_latest(self, symbol: str, timeframe: str = "5m") -> Optional[dict]:
        series = self._cache.get(str(symbol), {}).get(str(timeframe))
        if series and len(series):
            return series[-1]
        return None
