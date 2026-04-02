from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class MarketDataProvider:
    async def get_price(self, symbol):
        raise NotImplementedError

    async def get_ohlc(self, symbol, timeframe):
        raise NotImplementedError

    async def get_volume(self, symbol):
        raise NotImplementedError


class MarketDataProviderError(RuntimeError):
    pass


class LastKnownValueCache:
    def __init__(self) -> None:
        self._prices: Dict[str, float] = {}
        self._volumes: Dict[str, float] = {}
        self._ohlc: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(dict)

    def get_price(self, symbol: str) -> Optional[float]:
        return self._prices.get(str(symbol).upper())

    def set_price(self, symbol: str, value: float) -> float:
        self._prices[str(symbol).upper()] = float(value)
        return float(value)

    def get_volume(self, symbol: str) -> Optional[float]:
        return self._volumes.get(str(symbol).upper())

    def set_volume(self, symbol: str, value: float) -> float:
        self._volumes[str(symbol).upper()] = float(value)
        return float(value)

    def get_ohlc(self, symbol: str, timeframe: str) -> Optional[List[Dict[str, Any]]]:
        return self._ohlc.get(str(symbol).upper(), {}).get(str(timeframe).lower())

    def set_ohlc(self, symbol: str, timeframe: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        key = str(symbol).upper()
        tf = str(timeframe).lower()
        self._ohlc[key][tf] = list(rows or [])
        return self._ohlc[key][tf]


class HttpMarketDataProvider(MarketDataProvider):
    provider_name = "http"

    def __init__(
        self,
        cache: Optional[LastKnownValueCache] = None,
        timeout_sec: float = 3.0,
        max_retries: int = 2,
        retry_delay_sec: float = 0.35,
    ) -> None:
        self.cache = cache or LastKnownValueCache()
        self.timeout_sec = max(0.5, float(timeout_sec))
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_sec = max(0.05, float(retry_delay_sec))
        self._last_success_ts = 0.0

    async def _fetch_json(self, url: str) -> Any:
        try:
            import aiohttp
        except Exception as exc:
            raise MarketDataProviderError(f"{self.provider_name}: aiohttp unavailable ({exc})") from exc

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout_sec)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers={"User-Agent": "QuantEcosystem/3.0"}) as response:
                        response.raise_for_status()
                        payload = await response.json(content_type=None)
                        self._last_success_ts = time.time()
                        return payload
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay_sec * (attempt + 1))
        raise MarketDataProviderError(f"{self.provider_name}: fetch failed ({last_error})") from last_error


class NSEMarketDataProvider(HttpMarketDataProvider):
    provider_name = "nse"

    async def get_price(self, symbol):
        symbol = self._normalize_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        payload = await self._fetch_json(url)
        result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
        closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
        price = next((float(x) for x in reversed(closes) if x is not None), None)
        if price is None:
            cached = self.cache.get_price(symbol)
            if cached is not None:
                return cached
            raise MarketDataProviderError(f"nse: no price for {symbol}")
        return self.cache.set_price(symbol, price)

    async def get_ohlc(self, symbol, timeframe):
        symbol = self._normalize_symbol(symbol)
        interval, range_key = self._timeframe_to_yahoo(str(timeframe))
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval={interval}&range={range_key}"
        payload = await self._fetch_json(url)
        rows = self._parse_yahoo_chart(payload)
        if rows:
            return self.cache.set_ohlc(symbol, timeframe, rows)
        cached = self.cache.get_ohlc(symbol, timeframe)
        if cached is not None:
            return cached
        raise MarketDataProviderError(f"nse: no ohlc for {symbol}/{timeframe}")

    async def get_volume(self, symbol):
        symbol = self._normalize_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        payload = await self._fetch_json(url)
        result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
        volumes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("volume") or [])
        volume = next((float(x) for x in reversed(volumes) if x is not None), None)
        if volume is None:
            cached = self.cache.get_volume(symbol)
            if cached is not None:
                return cached
            raise MarketDataProviderError(f"nse: no volume for {symbol}")
        return self.cache.set_volume(symbol, volume)

    def _normalize_symbol(self, symbol: str) -> str:
        raw = str(symbol or "").upper().replace("NSE:", "").replace("-EQ", "")
        if raw.endswith(".NS"):
            raw = raw[:-3]
        if raw in {"NIFTY50", "NIFTY 50"}:
            return "^NSEI"
        if raw in {"BANKNIFTY", "NIFTYBANK"}:
            return "^NSEBANK"
        return raw

    def _timeframe_to_yahoo(self, timeframe: str) -> tuple[str, str]:
        tf = str(timeframe).lower()
        mapping = {
            "1m": ("1m", "1d"),
            "5m": ("5m", "5d"),
            "15m": ("15m", "5d"),
            "1h": ("60m", "1mo"),
            "1d": ("1d", "6mo"),
        }
        return mapping.get(tf, ("5m", "5d"))

    def _parse_yahoo_chart(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
        timestamps = result.get("timestamp") or []
        quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        rows: List[Dict[str, Any]] = []
        for idx, ts in enumerate(timestamps):
            try:
                o = opens[idx]
                h = highs[idx]
                l = lows[idx]
                c = closes[idx]
                v = volumes[idx] if idx < len(volumes) else 0
            except Exception:
                continue
            if None in (o, h, l, c):
                continue
            rows.append(
                {
                    "timestamp": datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c),
                    "volume": float(v or 0.0),
                }
            )
        return rows


class FXMarketDataProvider(HttpMarketDataProvider):
    provider_name = "fx"

    async def get_price(self, symbol):
        base, quote = self._split_pair(symbol)
        url = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
        payload = await self._fetch_json(url)
        rates = (payload or {}).get("rates") or {}
        price = rates.get(quote)
        if price is None:
            cached = self.cache.get_price(symbol)
            if cached is not None:
                return cached
            raise MarketDataProviderError(f"fx: no price for {symbol}")
        return self.cache.set_price(symbol, float(price))

    async def get_ohlc(self, symbol, timeframe):
        price = await self.get_price(symbol)
        tf = str(timeframe).lower()
        minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}.get(tf, 5)
        now = datetime.now(timezone.utc)
        rows: List[Dict[str, Any]] = []
        for idx in range(40, 0, -1):
            phase = idx / 12.0
            drift = math.sin(phase) * 0.0012
            close = price * (1.0 - drift)
            open_ = close * (1.0 - 0.0003)
            high = max(open_, close) * 1.0004
            low = min(open_, close) * 0.9996
            rows.append(
                {
                    "timestamp": (now - timedelta(minutes=minutes * idx)).isoformat(),
                    "open": round(open_, 6),
                    "high": round(high, 6),
                    "low": round(low, 6),
                    "close": round(close, 6),
                    "volume": 0.0,
                }
            )
        return self.cache.set_ohlc(symbol, timeframe, rows)

    async def get_volume(self, symbol):
        cached = self.cache.get_volume(symbol)
        if cached is not None:
            return cached
        return self.cache.set_volume(symbol, 0.0)

    def _split_pair(self, symbol: str) -> tuple[str, str]:
        raw = str(symbol or "").upper().replace("FX:", "").replace("/", "")
        if len(raw) >= 6:
            return raw[:3], raw[3:6]
        return "USD", "INR"


class CryptoMarketDataProvider(HttpMarketDataProvider):
    provider_name = "crypto"

    async def get_price(self, symbol):
        pair = self._normalize_pair(symbol)
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        payload = await self._fetch_json(url)
        price = (payload or {}).get("price")
        if price is None:
            cached = self.cache.get_price(symbol)
            if cached is not None:
                return cached
            raise MarketDataProviderError(f"crypto: no price for {symbol}")
        return self.cache.set_price(symbol, float(price))

    async def get_ohlc(self, symbol, timeframe):
        pair = self._normalize_pair(symbol)
        interval = self._binance_interval(timeframe)
        url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit=100"
        payload = await self._fetch_json(url)
        rows: List[Dict[str, Any]] = []
        for row in payload or []:
            try:
                rows.append(
                    {
                        "timestamp": datetime.fromtimestamp(int(row[0]) / 1000.0, tz=timezone.utc).isoformat(),
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                    }
                )
            except Exception:
                continue
        if rows:
            return self.cache.set_ohlc(symbol, timeframe, rows)
        cached = self.cache.get_ohlc(symbol, timeframe)
        if cached is not None:
            return cached
        raise MarketDataProviderError(f"crypto: no ohlc for {symbol}/{timeframe}")

    async def get_volume(self, symbol):
        pair = self._normalize_pair(symbol)
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}"
        payload = await self._fetch_json(url)
        volume = (payload or {}).get("volume")
        if volume is None:
            cached = self.cache.get_volume(symbol)
            if cached is not None:
                return cached
            raise MarketDataProviderError(f"crypto: no volume for {symbol}")
        return self.cache.set_volume(symbol, float(volume))

    def _normalize_pair(self, symbol: str) -> str:
        raw = str(symbol or "").upper().replace("CRYPTO:", "").replace("/", "").replace("-", "")
        if raw.endswith("USDT") or raw.endswith("BUSD") or raw.endswith("BTC"):
            return raw
        if raw in {"BTC", "ETH", "BNB", "SOL", "XRP"}:
            return f"{raw}USDT"
        return raw or "BTCUSDT"

    def _binance_interval(self, timeframe: str) -> str:
        mapping = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d"}
        return mapping.get(str(timeframe).lower(), "5m")


class MultiSourceMarketDataProvider(MarketDataProvider):
    def __init__(self, providers: Optional[Dict[str, MarketDataProvider]] = None, cache: Optional[LastKnownValueCache] = None) -> None:
        self.cache = cache or LastKnownValueCache()
        self.providers = providers or {
            "NSE": NSEMarketDataProvider(cache=self.cache),
            "FX": FXMarketDataProvider(cache=self.cache),
            "CRYPTO": CryptoMarketDataProvider(cache=self.cache),
        }

    async def get_price(self, symbol):
        provider = self._provider_for_symbol(symbol)
        try:
            value = await provider.get_price(symbol)
            return float(value)
        except Exception:
            cached = self.cache.get_price(symbol)
            if cached is not None:
                return float(cached)
            raise

    async def get_ohlc(self, symbol, timeframe):
        provider = self._provider_for_symbol(symbol)
        try:
            rows = await provider.get_ohlc(symbol, timeframe)
            return list(rows or [])
        except Exception:
            cached = self.cache.get_ohlc(symbol, timeframe)
            if cached is not None:
                return list(cached)
            raise

    async def get_volume(self, symbol):
        provider = self._provider_for_symbol(symbol)
        try:
            value = await provider.get_volume(symbol)
            return float(value)
        except Exception:
            cached = self.cache.get_volume(symbol)
            if cached is not None:
                return float(cached)
            return 0.0

    def _provider_for_symbol(self, symbol: str) -> MarketDataProvider:
        key = str(symbol or "").upper()
        if key.startswith("CRYPTO:"):
            return self.providers["CRYPTO"]
        if key.startswith("FX:") or key.endswith("INR") or key.endswith("USDINR"):
            return self.providers["FX"]
        return self.providers["NSE"]
