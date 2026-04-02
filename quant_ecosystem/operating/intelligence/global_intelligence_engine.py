"""
Global intelligence engine.
"""

from __future__ import annotations
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GlobalIntelligenceEngine:
    """Aggregates macro signals and cross-asset intelligence."""

    def __init__(self, config=None, market_data=None, **kwargs):
        self.config = config
        self.market_data = market_data

    def set_market_data(self, engine):
        self.market_data = engine

    def _build_intelligence(self, price: float):
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "regime": "TREND",
            "bias": "BULL" if price and price > 0 else "NEUTRAL",
            "latest_price": float(price),
            "volume": 0.0,
            "volatility": 0.0,
        }

    def get_latest_price(self, symbol: str):
        if self.market_data:
            try:
                price = self.market_data.get_price_sync(symbol)
                return self._build_intelligence(price)
            except Exception as e:
                logger.warning(f"Price fetch failed: {e}")

        return self._build_intelligence(0.0)

    def get_volume(self, symbol: str):
        return 0.0

    def get_volatility(self, symbol: str, lookback: int = 20):
        return 0.0

    def analyze(self, symbol=None, snapshots=None, macro_inputs=None):
        """
        Always return structured intelligence dict.
        """
        if not self.market_data:
            return self._build_intelligence(0.0)

        try:
            # Use provided symbol or default
            target_symbol = symbol or "FX:USDINR"
            closes = []
            if hasattr(self.market_data, "get_close_series"):
                closes = list(self.market_data.get_close_series(target_symbol, lookback=50) or [])

            if not closes and hasattr(self.market_data, "_price_history"):
                closes = list(getattr(self.market_data, "_price_history", {}).get(target_symbol, []) or [])

            latest_price = float(closes[-1]) if closes else 0.0
            print(f"[DATA FLOW] symbol={target_symbol} closes_len={len(closes)} latest={latest_price}")

            returns = []
            for i in range(1, len(closes)):
                prev = closes[i - 1]
                if prev > 0:
                    returns.append((closes[i] - prev) / prev)

            volatility = (
                (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5
                if returns else 0.0
            )

            trend_strength = ((closes[-1] - closes[0]) / closes[0]) if closes and closes[0] != 0 else 0.0
            confidence = min(1.0, abs(trend_strength) * 5 + volatility * 10)
            if confidence <= 0.0:
                confidence = 0.3

            regime = "TREND" if trend_strength > 0 else "RANGE"
            bias = "BULL" if trend_strength > 0 else "NEUTRAL"

            # Determine market from symbol
            market = "UNKNOWN"
            if target_symbol.startswith("FX:"):
                market = "FX"
            elif target_symbol.startswith("NSE:"):
                market = "EQUITY"
            elif "USDT" in target_symbol or "BTC" in target_symbol or "ETH" in target_symbol:
                market = "CRYPTO"

            return {
                "symbol": target_symbol,
                "market": market,
                "timestamp": datetime.utcnow().isoformat(),
                "regime": regime,
                "bias": bias,
                "latest_price": latest_price,
                "volatility": volatility,
                "trend_strength": trend_strength,
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Global intelligence failed: {e}")
            return self._build_intelligence(0.0)

    def _compute_volatility(self, prices):
        if not prices or len(prices) < 2:
            return 0.0

        returns = []
        for i in range(1, len(prices)):
            prev = prices[i-1]
            if prev > 0:
                returns.append((prices[i] - prev) / prev)

        if not returns:
            return 0.0

        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)

        return variance ** 0.5     

    def _compute_trend_strength(self, prices):
        if not prices or len(prices) < 5:
            return 0.0

        return (prices[-1] - prices[0]) / max(prices[0], 1e-6)       