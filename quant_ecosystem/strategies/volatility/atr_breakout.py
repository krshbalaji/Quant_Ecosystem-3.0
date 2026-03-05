from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class ATRBreakoutStrategy(BaseStrategy):
    """
    ATR-based volatility breakout strategy.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None):
        default_params: Dict[str, object] = {
            "atr_length": 14,
            "atr_mult": 2.0,
            "stop_loss_mult": 1.0,
            "take_profit_mult": 2.0,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="atr_breakout",
            name="ATR Breakout",
            family="volatility",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def generate_signal(self, market_data) -> Optional[Signal]:
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        if not symbols:
            return None

        symbol = symbols[0]
        length = int(max(5, float(self.params.get("atr_length", 14))))
        # For now we approximate ATR using close-only series, which is conservative.
        closes = market_data.get_series(symbol=symbol, timeframe="5m", lookback=length + 5)
        if len(closes) < length + 2:
            return None

        df = pd.DataFrame({"close": closes})
        df["prev_close"] = df["close"].shift(1)
        # Proxy ATR using absolute close-to-close changes.
        tr = (df["close"] - df["prev_close"]).abs()
        atr = tr.rolling(length).mean()
        last_atr = float(atr.iloc[-1])
        price = float(df["close"].iloc[-1])

        if last_atr <= 0:
            return None

        mult = float(self.params.get("atr_mult", 2.0))
        upper = price + mult * last_atr
        lower = price - mult * last_atr

        side: Optional[str] = None
        if price >= upper:
            side = "BUY"
        elif price <= lower:
            side = "SELL"

        if not side:
            return None

        sl_mult = float(self.params.get("stop_loss_mult", 1.0))
        tp_mult = float(self.params.get("take_profit_mult", 2.0))

        if side == "BUY":
            stop_loss = price - sl_mult * last_atr
            take_profit = price + tp_mult * last_atr
        else:
            stop_loss = price + sl_mult * last_atr
            take_profit = price - tp_mult * last_atr

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

