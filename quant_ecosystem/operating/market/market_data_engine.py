from __future__ import annotations

from datetime import datetime
import asyncio
import math
import random

from quant_ecosystem.operating.market.nse_market_provider import NSEMarketDataProvider


class MarketDataEngine:

    def __init__(self, config=None, universe=None):
        self.config = config
        self.universe = universe

        self._synthetic_prices = {}
        self._last_price_cache = {}
        self._price_history = {}

        self._real_provider = NSEMarketDataProvider()
        self.use_real_data = False   # 🔥 FORCE synthetic for now

    # -----------------------------
    # CORE START / STOP
    # -----------------------------

    def start(self):
        print("[MarketDataEngine] Starting feed...")

    def stop(self):
        print("[MarketDataEngine] Stopping feed...")

    # -----------------------------
    # ASYNC PRICE FETCH
    # -----------------------------

    async def get_price(self, symbol: str):

        if self.use_real_data:
            try:
                data = await self._real_provider.get_price(symbol)
                if data and "price" in data:
                    price = float(data["price"])
                    self._last_price_cache[symbol] = price
                    self._price_history.setdefault(symbol, []).append(price)
                    return price
            except Exception:
                pass

        return self._get_synthetic_price(symbol)

    # -----------------------------
    # SYNC ADAPTER (FIXED)
    # -----------------------------

    def get_price_sync(self, symbol: str):

        # 🔥 ALWAYS generate price (no empty cache issue)
        return self._get_synthetic_price(symbol)

    # -----------------------------
    # SYNTHETIC ENGINE (FIXED)
    # -----------------------------

    def _get_synthetic_price(self, symbol: str):

        base = self._synthetic_prices.get(symbol, 100.0)

        drift = 0.0005
        shock = random.uniform(-0.005, 0.005)

        new_price = base * (1 + drift + shock)

        self._synthetic_prices[symbol] = new_price
        self._last_price_cache[symbol] = new_price

        history = self._price_history.setdefault(symbol, [])
        history.append(new_price)

        if len(history) > 200:
            history.pop(0)

        return new_price

    # -----------------------------
    # SERIES DATA (CRITICAL FIX)
    # -----------------------------

    def get_close_series(self, symbol, lookback=100):

        history = self._price_history.get(symbol, [])

        if len(history) < 2:
            # force warmup
            for _ in range(lookback):
                self._get_synthetic_price(symbol)
            history = self._price_history.get(symbol, [])

        return history[-lookback:]

    # -----------------------------
    # OTHER METHODS
    # -----------------------------

    def fetch(self, symbol: str):
        return {
            "symbol": symbol,
            "price": self.get_price_sync(symbol),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_universe(self):
        if self.universe and hasattr(self.universe, "get_symbols"):
            return self.universe.get_symbols()
        return self.universe or []

    def get_market_data(self):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "symbols": list(self.get_universe())
        }

    def get_volume(self, symbol: str):
        return 0.0

    def get_volatility(self, symbol: str, lookback: int = 20):

        closes = self.get_close_series(symbol, lookback)

        if len(closes) < 2:
            return 0.0

        returns = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            if prev > 0:
                returns.append((closes[i] - prev) / prev)

        if not returns:
            return 0.0

        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)

        return float(math.sqrt(variance))