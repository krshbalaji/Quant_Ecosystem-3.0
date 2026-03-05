from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI-based mean reversion strategy.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None):
        default_params: Dict[str, object] = {
            "rsi_length": 14,
            "oversold": 30.0,
            "overbought": 70.0,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 1.5,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="rsi_reversion",
            name="RSI Mean Reversion",
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
        length = int(max(5, float(self.params.get("rsi_length", 14))))
        closes = market_data.get_series(symbol=symbol, timeframe="5m", lookback=length + 5)
        if len(closes) < length + 1:
            return None

        df = pd.DataFrame({"close": closes})
        delta = df["close"].diff()
        gain = delta.clip(lower=0.0).rolling(length).mean()
        loss = (-delta.clip(upper=0.0)).rolling(length).mean()
        rs = gain / loss.replace(0, float("inf"))
        rsi = 100.0 - (100.0 / (1.0 + rs))
        value = float(rsi.iloc[-1])

        side: Optional[str] = None
        if value <= float(self.params.get("oversold", 30.0)):
            side = "BUY"
        elif value >= float(self.params.get("overbought", 70.0)):
            side = "SELL"

        if not side:
            return None

        price = float(closes[-1])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 1.0)) / 100.0
        take_profit_pct = float(self.params.get("take_profit_pct", 1.5)) / 100.0

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

