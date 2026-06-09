from __future__ import annotations

from typing import Dict, Optional
from typing import cast

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class BollingerReversionStrategy(BaseStrategy):
    """
    Bollinger-band based mean reversion strategy.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 20,
            "num_std": 2.0,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 1.5,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="bollinger_reversion",
            name="Bollinger Reversion",
            family="mean_reversion",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def generate_signal(self, market_data) -> Optional[Signal]:
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        if not symbols:
            return None

        symbol = symbols[0]

        lookback_raw = self.params.get("lookback", 20)
        lookback = int(max(5, float(cast(float | int, lookback_raw))))

        closes = market_data.get_series(
            symbol=symbol,
            timeframe="5m",
            lookback=lookback + 2,
        )

        if len(closes) < lookback:
            return None

        df = pd.DataFrame({"close": closes})

        close_values = df["close"].to_numpy(dtype=float)

        ma = df["close"].rolling(lookback).mean()
        std = df["close"].rolling(lookback).std()

        num_std = float(cast(float | int, self.params.get("num_std", 2.0)))

        upper = ma + num_std * std
        lower = ma - num_std * std

        last_close = float(close_values[-1])
        last_upper = float(list(upper)[-1])
        last_lower = float(list(lower)[-1])

        side: Optional[str] = None
        if last_close <= last_lower:
            side = "BUY"
        elif last_close >= last_upper:
            side = "SELL"

        if not side:
            return None

        lookback_raw = self.params.get("lookback", 20)
        lookback = int(max(5, float(cast(float | int, lookback_raw))))

        num_std = float(cast(float | int, self.params.get("num_std", 2.0)))

        stop_loss_pct = (
            float(cast(float | int, self.params.get("stop_loss_pct", 1.0)))
            / 100.0
        )

        take_profit_pct = (
            float(cast(float | int, self.params.get("take_profit_pct", 1.5)))
            / 100.0
        )

        if side == "BUY":
            stop_loss = last_close * (1.0 - stop_loss_pct)
            take_profit = last_close * (1.0 + take_profit_pct)
        else:
            stop_loss = last_close * (1.0 + stop_loss_pct)
            take_profit = last_close * (1.0 - take_profit_pct)

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

