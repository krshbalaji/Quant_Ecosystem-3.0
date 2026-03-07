from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class EMATrendStrategy(BaseStrategy):
    """
    Simple institutional-grade EMA crossover trend strategy.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "fast_ema": 20,
            "slow_ema": 50,
            "risk_per_trade_pct": 1.0,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 2.0,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="ema_trend",
            name="EMA Trend",
            family="trend",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def generate_signal(self, market_data) -> Optional[Signal]:
        """
        Expect market_data to provide:
        - get_series(symbol, timeframe, lookback)
        - get_latest_price(symbol)
        """
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        if not symbols:
            return None

        symbol = symbols[0]
        closes = market_data.get_series(symbol=symbol, timeframe="5m", lookback=200)
        if len(closes) < 60:
            return None

        df = pd.DataFrame({"close": closes})
        fast = int(self.params.get("fast_ema", 20))
        slow = int(self.params.get("slow_ema", 50))
        fast = max(3, fast)
        slow = max(fast + 1, slow)

        df["ema_fast"] = df["close"].ewm(span=fast).mean()
        df["ema_slow"] = df["close"].ewm(span=slow).mean()

        last_fast = float(df["ema_fast"].iloc[-1])
        last_slow = float(df["ema_slow"].iloc[-1])
        price = float(closes[-1])

        side: Optional[str] = None
        if last_fast > last_slow:
            side = "BUY"
        elif last_fast < last_slow:
            side = "SELL"

        if not side:
            return None

        stop_loss_pct = float(self.params.get("stop_loss_pct", 1.0)) / 100.0
        take_profit_pct = float(self.params.get("take_profit_pct", 2.0)) / 100.0

        if side == "BUY":
            stop_loss = price * (1.0 - stop_loss_pct)
            take_profit = price * (1.0 + take_profit_pct)
        else:
            stop_loss = price * (1.0 + stop_loss_pct)
            take_profit = price * (1.0 - take_profit_pct)

        signal: Signal = {
            "symbol": symbol,
            "side": side,
            "strength": 1.0,
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }

        return signal if self.validate_signal(signal) else None

import pandas as pd

class EMATrendStrategy:

    id = "ema_trend"

    def generate_signal(self, candles):

        if not candles or len(candles) < 50:
            return None

        df = pd.DataFrame(candles)

        df["ema_fast"] = df["close"].ewm(span=20).mean()
        df["ema_slow"] = df["close"].ewm(span=50).mean()

        if df["ema_fast"].iloc[-1] > df["ema_slow"].iloc[-1]:
            return "BUY"

        if df["ema_fast"].iloc[-1] < df["ema_slow"].iloc[-1]:
            return "SELL"

        return None