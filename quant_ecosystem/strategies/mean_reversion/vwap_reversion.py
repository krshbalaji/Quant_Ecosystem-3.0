from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class VWAPReversionStrategy(BaseStrategy):
    """
    VWAP deviation mean-reversion strategy.
    Buys when price is sufficiently below VWAP, sells when above.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 30,
            "deviation_pct": 0.3,
            "stop_loss_pct": 0.8,
            "take_profit_pct": 1.2,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="vwap_reversion",
            name="VWAP Reversion",
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
        lookback = int(max(5, float(self.params.get("lookback", 30))))

        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is not None:
            vwap = feature_engine.get_vwap(symbol, timeframe="5m", lookback=lookback)
            closes = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback)
        else:
            closes = market_data.get_series(symbol=symbol, timeframe="5m", lookback=lookback)
            if not closes:
                return None
            df = pd.DataFrame({"close": closes})
            vwap = float(df["close"].mean())

        if not closes:
            return None

        price = float(closes[-1])
        if vwap <= 0:
            return None

        deviation = (price - vwap) / vwap * 100.0
        threshold = float(self.params.get("deviation_pct", 0.3))

        side: Optional[str] = None
        if deviation <= -threshold:
            side = "BUY"
        elif deviation >= threshold:
            side = "SELL"

        if not side:
            return None

        stop_loss_pct = float(self.params.get("stop_loss_pct", 0.8)) / 100.0
        take_profit_pct = float(self.params.get("take_profit_pct", 1.2)) / 100.0

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

