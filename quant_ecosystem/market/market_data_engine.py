import asyncio
import logging
import random
from collections import defaultdict, deque

from quant_ecosystem.market.fyers_feed import FyersFeed
from quant_ecosystem.market.market_cache import MarketCache
from quant_ecosystem.market.candle_builder import CandleBuilder
from quant_ecosystem.market.data_source_router import DataSourceRouter

logger = logging.getLogger(__name__)


class MarketDataEngine:
    """
    Central market data provider for the ecosystem.

    Responsibilities:
    - Fetch candles from the broker or generate synthetic series
    - Maintain rolling OHLCV history
    - Provide snapshots and latest ticks to downstream engines
    """

    def __init__(
        self,
        broker=None,
        symbols=None,
        universe_manager=None,
        timeframe: str = "5m",
        history: int = 500
    ):
        # Broker is optional: when omitted, the engine operates in
        # synthetic mode, generating internal OHLCV series. When a
        # broker is provided, it will be used for live candles if
        # the broker exposes a compatible API.
        self.broker = broker
        self.universe_manager = universe_manager
        self.symbols = symbols or ["NSE:NIFTY50-INDEX"]
        self.timeframe = timeframe
        self.history_size = int(history)
        self.router = DataSourceRouter(broker)
        self.cache = MarketCache()
        self.builder = CandleBuilder()

        # Rolling OHLCV buffers per symbol
        self._data = defaultdict(
            lambda: {
                "open": deque(maxlen=self.history_size),
                "high": deque(maxlen=self.history_size),
                "low": deque(maxlen=self.history_size),
                "close": deque(maxlen=self.history_size),
                "volume": deque(maxlen=self.history_size),
            }
        )

        # Lightweight synthetic series used when the broker does not
        # provide historical candles. This keeps the rest of the
        # ecosystem running for research/demo purposes.
        self._synthetic_series = {}
        self._rng = random.Random()

        self.running = False

    async def start(self):
        logger.info("MarketDataEngine started")
        self.running = True

        while self.running:
            try:
                await self.update_market_data()
            except Exception as exc:
                logger.warning(f"MarketDataEngine error: {exc}")

            await asyncio.sleep(2)

            candles = self.router.fetch(symbol, timeframe)
            
    async def update_market_data(self):
        """
        Poll the broker for the latest candles and feed them into the cache.
        """
        for symbol in list(self.symbols or []):
            raw = self.feed.get_candles(symbol)
            candles = self.builder.build_from_fyers(raw or {})
            for c in candles:
                self.cache.update(symbol, c, timeframe=self.timeframe)

    # ------------------------------------------------------------------
    # Institutional public API
    # ------------------------------------------------------------------

    def get_latest_price(self, symbol: str) -> float | None:
        """
        Latest traded price for a symbol, if any.
        """
        latest = self.cache.get_latest(symbol, timeframe=self.timeframe)
        if latest is None:
            snap = self.get_snapshot(symbol=symbol)
            closes = list(snap.get("close") or [])
            return float(closes[-1]) if closes else None
        return float(latest.get("close"))

    def get_series(self, symbol: str, timeframe: str = "5m", lookback: int = 200):
        """
        Return a rolling close-price series for the given symbol/timeframe.
        """
        candles = self.cache.get_series(symbol, timeframe=timeframe, lookback=lookback)
        return [c.get("close") for c in candles if "close" in c]

    def get_latest(self, symbol: str):
        """
        Backwards-compatible accessor used by some callers.
        """
        return self.cache.get_latest(symbol, timeframe=self.timeframe)
    
        # Priority 1: Universe manager
        if self.universe_manager is not None:
            try:
                symbols = list(self.universe_manager.get_symbols() or [])
            except Exception:
                symbols = []

        # Priority 2: direct symbol list
        if not symbols:
            symbols = list(self.symbols or [])

        if not symbols:
            return

        for symbol in symbols:
            candles = None

            # Broker provides batched candles for a list of symbols
            if hasattr(self.broker, "get_candles"):
                try:
                    candles = self.broker.get_candles(symbol, self.timeframe)
                except TypeError:
                    # Fallback to batched signature (symbols=[...])
                    try:
                        batch = self.broker.get_candles(symbols=[symbol], timeframe=self.timeframe)
                        candles = batch.get(symbol) if isinstance(batch, dict) else None
                    except Exception:
                        candles = None
                except Exception:
                    candles = None
            elif hasattr(self.broker, "fetch_ohlc"):
                try:
                    candles = self.broker.fetch_ohlc(symbol, self.timeframe)
                except Exception:
                    candles = None

            if candles:
                self._ingest_candles(symbol, candles)
            else:
                # Ensure synthetic series continues to tick even if
                # live candles are unavailable.
                self._update_synthetic_tick(symbol)

        if self._data:
            logger.info("Market data updated for %d symbols", len(self._data))

    # ------------------------------------------------------------------
    # Public API used by other engines
    # ------------------------------------------------------------------

    def get_market_data(self):
        """
        Returns the latest OHLCV snapshot for all symbols as a
        symbol -> series mapping.
        """
        return self.get_snapshot()

    def get_latest_tick(self, symbol=None):
        """
        Returns the latest price tick for the given symbol.
        If no symbol is provided, the first available symbol is used.
        """
        snapshot = self.get_snapshot()
        if not snapshot:
            return None

        if symbol is None:
            symbol = next(iter(snapshot.keys()), None)
            if symbol is None:
                return None

        row = snapshot.get(symbol)
        if not row:
            return None

        closes = list(row.get("close") or [])
        if not closes:
            return None
        return closes[-1]

    def get_snapshot(self, symbol=None, timeframe: str | None = None, lookback: int = 60):
        """
        Returns a rolling snapshot of OHLCV data.

        - If symbol is None, returns a mapping of symbol -> OHLCV lists.
        - If symbol is provided, returns a single OHLCV dict.
        """
        if symbol is not None:
            data = self._data.get(symbol)
            if not data:
                return {
                    "open": [],
                    "high": [],
                    "low": [],
                    "close": [],
                    "volume": [],
                }
            return {
                key: list(values)[-lookback:]
                for key, values in data.items()
            }

        snapshot = {}
        for sym, data in self._data.items():
            snapshot[sym] = {
                key: list(values)[-lookback:]
                for key, values in data.items()
            }
        return snapshot

    def get_close_series(self, symbol, lookback: int = 50):
        """
        Convenience helper used by regime and execution engines.
        """
        snap = self.get_snapshot(symbol=symbol, lookback=lookback)
        return list(snap.get("close") or [])

    # ------------------------------------------------------------------
    # Simple analytics helpers used by intelligence layers
    # ------------------------------------------------------------------

    def get_volatility(self, symbol: str = "NSE:NIFTY50-INDEX", lookback: int = 40):
        """
        Approximate realised volatility (in percent) for the given symbol.
        Falls back to synthetic data if needed.
        """
        closes = self.get_close_series(symbol, lookback=lookback)
        if len(closes) < 2:
            return 1.0

        returns = []
        for idx in range(1, len(closes)):
            prev = float(closes[idx - 1])
            cur = float(closes[idx])
            if prev == 0:
                continue
            returns.append((cur - prev) / prev)

        if not returns:
            return 1.0

        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        return max(std_dev * 100.0, 0.01)

    def get_trend(self, symbol: str = "NSE:NIFTY50-INDEX", short: int = 5, long: int = 20):
        """
        Simple moving-average based trend proxy:
        - 1  -> uptrend
        - -1 -> downtrend
        - 0  -> neutral
        """
        closes = self.get_close_series(symbol, lookback=max(short, long) * 2)
        if len(closes) < short + 1:
            return 0

        short_ma = sum(closes[-short:]) / float(short)
        long_window = min(len(closes), long)
        long_ma = sum(closes[-long_window:]) / float(long_window)

        if long_ma == 0:
            return 0

        if short_ma > long_ma * 1.001:
            return 1
        if short_ma < long_ma * 0.999:
            return -1
        return 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ingest_candles(self, symbol, candles):
        """
        Normalise broker candle payloads into internal OHLCV buffers.
        Accepts either:
        - list of OHLCV dicts
        - dict with 'open','high','low','close','volume' lists
        - single OHLCV dict
        """
        buf = self._data[symbol]

        # Dict of lists
        if isinstance(candles, dict) and all(k in candles for k in ("open", "high", "low", "close", "volume")):
            length = len(candles["close"])
            for idx in range(length):
                buf["open"].append(candles["open"][idx])
                buf["high"].append(candles["high"][idx])
                buf["low"].append(candles["low"][idx])
                buf["close"].append(candles["close"][idx])
                buf["volume"].append(candles["volume"][idx])
            return

        # List of dicts
        if isinstance(candles, (list, tuple)):
            for row in candles:
                if not isinstance(row, dict):
                    continue
                buf["open"].append(row.get("open"))
                buf["high"].append(row.get("high"))
                buf["low"].append(row.get("low"))
                buf["close"].append(row.get("close"))
                buf["volume"].append(row.get("volume", 0))
            return

        # Single dict
        if isinstance(candles, dict):
            buf["open"].append(candles.get("open"))
            buf["high"].append(candles.get("high"))
            buf["low"].append(candles.get("low"))
            buf["close"].append(candles.get("close"))
            buf["volume"].append(candles.get("volume", 0))

    def _ensure_synthetic_series(self, symbol, seed_price=None):
        if symbol in self._synthetic_series:
            return
        base = float(seed_price or self._rng.uniform(100, 1000))
        history = deque(maxlen=self.history_size)
        for _ in range(min(100, self.history_size)):
            base *= 1 + self._rng.uniform(-0.003, 0.003)
            history.append(round(base, 4))
        self._synthetic_series[symbol] = history

    def _update_synthetic_tick(self, symbol):
        self._ensure_synthetic_series(symbol)
        history = self._synthetic_series[symbol]
        last = history[-1]
        next_price = last * (1 + self._rng.uniform(-0.004, 0.004))
        price = round(next_price, 4)
        history.append(price)

        buf = self._data[symbol]
        buf["open"].append(price)
        buf["high"].append(price)
        buf["low"].append(price)
        buf["close"].append(price)
        buf["volume"].append(0.0)