from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class DonchianTrendStrategy(BaseStrategy):
    """
    Donchian channel breakout trend strategy.
    Uses channel highs/lows over a lookback window to detect breakouts.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 20,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 2.0,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="donchian_trend",
            name="Donchian Trend",
            family="trend",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def generate_signal(self, market_data) -> Optional[Signal]:
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        if not symbols:
            return None

        symbol = symbols[0]
        lookback_value = self.params.get("lookback", 20)

        lookback = int(
            max(
                5,
                float(
                    lookback_value
                    if isinstance(lookback_value, (int, float))
                    else 20
                ),
            )
        )

        # Prefer feature engine if attached
        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is not None:
            closes = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback + 2)
        else:
            closes = market_data.get_series(symbol=symbol, timeframe="5m", lookback=lookback + 2)

        if len(closes) < lookback + 1:
            return None

        df = pd.DataFrame({"close": closes})
        window = df["close"].iloc[-lookback:]
        last = float(window.iloc[-1])
        high = float(window.max())
        low = float(window.min())

        side: Optional[str] = None
        if last >= high:
            side = "BUY"
        elif last <= low:
            side = "SELL"

        if not side:
            return None

        sl_value = self.params.get("stop_loss_pct", 1.0)

        stop_loss_pct = float(
            sl_value
            if isinstance(sl_value, (int, float))
            else 1.0
        ) / 100.0

        tp_value = self.params.get("take_profit_pct", 2.0)

        take_profit_pct = float(
            tp_value
            if isinstance(tp_value, (int, float))
            else 2.0
        ) / 100.0

        if side == "BUY":
            stop_loss = last * (1.0 - stop_loss_pct)
            take_profit = last * (1.0 + take_profit_pct)
        else:
            stop_loss = last * (1.0 + stop_loss_pct)
            take_profit = last * (1.0 - take_profit_pct)

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

