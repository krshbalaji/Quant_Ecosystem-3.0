"""Async market data adapter for global alpha scanner."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Iterable, List, Optional


class MarketDataAdapter:
    """Fetches market data from connected engines/adapters with safe fallbacks."""

    def __init__(self, market_data_engine=None, broker_router=None, max_concurrency: int = 64):
        self.market_data_engine = market_data_engine
        self.broker_router = broker_router
        self.max_concurrency = max(1, int(max_concurrency))

    async def fetch_many(self, instruments: Iterable[Dict], lookback: int = 80) -> List[Dict]:
        """Fetch market snapshots asynchronously for many symbols."""
        items = list(instruments)
        if not items:
            return []

        sem = asyncio.Semaphore(self.max_concurrency)

        async def run_one(instrument: Dict):
            async with sem:
                return await self.fetch_one(instrument, lookback=lookback)

        tasks = [asyncio.create_task(run_one(item)) for item in items]
        snapshots = await asyncio.gather(*tasks, return_exceptions=True)

        out = []
        for entry in snapshots:
            if isinstance(entry, Exception):
                continue
            if entry:
                out.append(entry)
        return out

    async def fetch_one(self, instrument: Dict, lookback: int = 80) -> Optional[Dict]:
        """Fetch one instrument snapshot containing OHLCV-like fields."""
        symbol = str(instrument.get("symbol", "")).strip()
        if not symbol:
            return None

        # Prefer local market data engine snapshot.
        if self.market_data_engine and hasattr(self.market_data_engine, "get_snapshot"):
            try:
                snap = self.market_data_engine.get_snapshot(symbol, lookback=lookback)
                close = list(snap.get("close", []))
                if close:
                    return self._normalize_snapshot(symbol, instrument, close, snap)
            except Exception:
                pass

        # Broker/trading API fallback if methods exist.
        broker = getattr(self.broker_router, "broker", None) if self.broker_router else None
        if broker and hasattr(broker, "get_ohlc"):
            try:
                # expected shape: {"close":[...], "high":[...], "low":[...], "volume":[...]}
                ohlc = broker.get_ohlc(symbol, lookback=lookback)
                close = list((ohlc or {}).get("close", []))
                if close:
                    return self._normalize_snapshot(symbol, instrument, close, ohlc or {})
            except Exception:
                pass

        return None

    def _normalize_snapshot(self, symbol: str, instrument: Dict, close: List[float], raw: Dict) -> Dict:
        high = list(raw.get("high", [value * 1.001 for value in close]))
        low = list(raw.get("low", [value * 0.999 for value in close]))
        volume = list(raw.get("volume", self._synthetic_volume(symbol, len(close))))
        spread = list(raw.get("spread", self._synthetic_spread(symbol, len(close))))
        price = float(close[-1])
        return {
            "symbol": symbol,
            "asset_class": instrument.get("asset_class", "stocks"),
            "group": instrument.get("group", ""),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "price": price,
            "close": close,
            "high": high[-len(close):],
            "low": low[-len(close):],
            "volume": volume[-len(close):],
            "spread": spread[-len(close):],
            "volatility": float(raw.get("volatility", self._realized_vol(close))),
            "depth_score": float(raw.get("depth_score", instrument.get("default_liquidity_score", 0.5))),
        }

    def _realized_vol(self, close: List[float]) -> float:
        if len(close) < 3:
            return 0.0
        rets = []
        for i in range(1, len(close)):
            prev = close[i - 1]
            cur = close[i]
            if prev == 0:
                continue
            rets.append((cur - prev) / prev)
        if not rets:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / len(rets)
        return (var ** 0.5) * 100.0

    def _synthetic_volume(self, symbol: str, size: int) -> List[float]:
        base = 10000.0
        if symbol.startswith("CRYPTO:"):
            base = 25000.0
        elif symbol.startswith("FX:"):
            base = 18000.0
        elif symbol.startswith("MCX:"):
            base = 12000.0
        return [base + ((i % 10) * base * 0.03) for i in range(size)]

    def _synthetic_spread(self, symbol: str, size: int) -> List[float]:
        if symbol.startswith("FX:"):
            s = 0.0002
        elif symbol.startswith("CRYPTO:"):
            s = 0.0015
        elif symbol.startswith("MCX:"):
            s = 0.05
        else:
            s = 0.03
        return [s for _ in range(size)]

