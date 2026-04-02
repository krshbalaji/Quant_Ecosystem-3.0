import asyncio
import logging
import time
import aiohttp
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from quant_ecosystem.operating.market.market_data_provider import MarketDataProvider

logger = logging.getLogger(__name__)

class NSEMarketDataProvider(MarketDataProvider):
    """NSE market data provider using Yahoo Finance API"""

    def __init__(
        self,
        timeout_sec: float = 3.0,
        max_retries: int = 3,
        retry_delay_sec: float = 0.5,
    ):
        self.timeout_sec = max(0.5, float(timeout_sec))
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_sec = max(0.05, float(retry_delay_sec))

    async def _fetch_json(self, url: str) -> Any:
        """Fetch JSON data with retry logic"""
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout_sec)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers={"User-Agent": "QuantEcosystem/3.0"}) as response:
                        response.raise_for_status()
                        payload = await response.json(content_type=None)
                        return payload
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay_sec * (attempt + 1))
        raise RuntimeError(f"NSE provider: fetch failed after {self.max_retries} retries ({last_error})") from last_error

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance"""
        raw = str(symbol or "").upper().replace("NSE:", "").replace("-EQ", "")
        if raw.endswith(".NS"):
            raw = raw[:-3]
        if raw in {"NIFTY50", "NIFTY 50"}:
            return "^NSEI"
        if raw in {"BANKNIFTY", "NIFTYBANK"}:
            return "^NSEBANK"
        return raw

    async def get_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        symbol = self._normalize_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"

        try:
            payload = await self._fetch_json(url)
            result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
            closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
            price = next((float(x) for x in reversed(closes) if x is not None), None)

            if price is not None:
                return round(float(price), 4)

        except Exception as exc:
            logger.debug(f"NSE price fetch failed for {symbol}: {exc}")

        # Return synthetic fallback
        return self._get_synthetic_price(symbol)

    async def get_ohlc(self, symbol: str, timeframe: str) -> list:
        """Get OHLC data for symbol and timeframe"""
        symbol = self._normalize_symbol(symbol)
        interval, range_key = self._timeframe_to_yahoo(str(timeframe))
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval={interval}&range={range_key}"

        try:
            payload = await self._fetch_json(url)
            rows = self._parse_yahoo_chart(payload)
            if rows:
                return rows
        except Exception as exc:
            logger.debug(f"NSE OHLC fetch failed for {symbol}/{timeframe}: {exc}")

        # Return synthetic fallback
        return self._get_synthetic_ohlc(symbol, timeframe)

    async def get_volume(self, symbol: str) -> float:
        """Get volume for symbol"""
        symbol = self._normalize_symbol(symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"

        try:
            payload = await self._fetch_json(url)
            result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
            volumes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("volume") or [])
            volume = next((float(x) for x in reversed(volumes) if x is not None), None)

            if volume is not None:
                return float(volume)

        except Exception as exc:
            logger.debug(f"NSE volume fetch failed for {symbol}: {exc}")

        # Return synthetic fallback
        return self._get_synthetic_volume(symbol)

    def _timeframe_to_yahoo(self, timeframe: str) -> tuple[str, str]:
        """Convert timeframe to Yahoo Finance format"""
        tf = str(timeframe).lower()
        mapping = {
            "1m": ("1m", "1d"),
            "5m": ("5m", "5d"),
            "15m": ("15m", "5d"),
            "1h": ("60m", "1mo"),
            "1d": ("1d", "6mo"),
        }
        return mapping.get(tf, ("5m", "5d"))

    def _parse_yahoo_chart(self, payload: Dict[str, Any]) -> list:
        """Parse Yahoo Finance chart data"""
        result = (((payload or {}).get("chart") or {}).get("result") or [{}])[0]
        timestamps = result.get("timestamp") or []
        quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        rows: list = []
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
            rows.append({
                "timestamp": datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(v or 0.0),
            })
        return rows

    def _get_synthetic_price(self, symbol: str) -> float:
        """Generate synthetic price as fallback"""
        key = str(symbol or "UNKNOWN").upper()
        seed = sum(ord(ch) for ch in key)
        base = 100.0 + float(seed % 900)
        phase = datetime.utcnow().second / 60.0
        import math
        drift = math.sin(phase * math.pi * 2.0) * 0.0025
        return round(base * (1.0 + drift), 4)

    def _get_synthetic_ohlc(self, symbol: str, timeframe: str) -> list:
        """Generate synthetic OHLC as fallback"""
        price = self._get_synthetic_price(symbol)
        now = datetime.now(timezone.utc)
        minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}.get(str(timeframe).lower(), 5)
        rows: list = []
        for idx in range(20, 0, -1):
            drift = 0.001 * (idx / 20.0)
            close = price * (1.0 - drift)
            open_ = close * (1.0 - 0.0005)
            high = max(open_, close) * 1.001
            low = min(open_, close) * 0.999
            rows.append({
                "timestamp": (now - timedelta(minutes=minutes * idx)).isoformat(),
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": 1000.0 + idx * 100,
            })
        return rows

    def _get_synthetic_volume(self, symbol: str) -> float:
        """Generate synthetic volume as fallback"""
        key = str(symbol or "UNKNOWN").upper()
        seed = sum(ord(ch) for ch in key)
        return 1000.0 + float(seed % 10000)