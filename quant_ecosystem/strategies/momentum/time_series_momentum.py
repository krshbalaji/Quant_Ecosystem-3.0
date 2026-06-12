from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class TimeSeriesMomentumStrategy(BaseStrategy):
    """
    Time-series momentum strategy.
    Trades a single symbol based on its own trend strength over a lookback window.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 40,
            "threshold": 0.02,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 2.0,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="time_series_momentum",
            name="Time-Series Momentum",
            family="momentum",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def generate_signal(self, market_data) -> Optional[Signal]:
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        if not symbols:
            return None

        symbol = symbols[0]
        lookback_value = self.params.get("lookback", 40)
        lookback = int(
            max(
                5,
                float(lookback_value if isinstance(lookback_value, (int, float)) else 40),
            )
        )

        threshold_value = self.params.get("threshold", 0.02)
        thresh = float(
            threshold_value if isinstance(threshold_value, (int, float)) else 0.02
        )

        sl_value = self.params.get("stop_loss_pct", 1.0)
        stop_loss_pct = float(
            sl_value if isinstance(sl_value, (int, float)) else 1.0
        ) / 100.0

        tp_value = self.params.get("take_profit_pct", 2.0)
        take_profit_pct = float(
            tp_value if isinstance(tp_value, (int, float)) else 2.0
        ) / 100.0
        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is not None:
            series = feature_engine.get_close_series(
                symbol,
                timeframe="5m",
                lookback=lookback + 1,
            )
        else:
            series = market_data.get_series(
                symbol=symbol,
                timeframe="5m",
                lookback=lookback + 1,
            )

        if len(series) < lookback + 1:
            return None

        arr = np.array(series[-lookback:], dtype=float)

        if arr[0] == 0:
            return None

        ret = (arr[-1] - arr[0]) / abs(arr[0])

        side: Optional[str] = None

        if ret > thresh:
            side = "BUY"
        elif ret < -thresh:
            side = "SELL"

        if not side:
            return None

        price = float(arr[-1])
        if side == "BUY":
            stop_loss = price * (1.0 - stop_loss_pct)
            take_profit = price * (1.0 + take_profit_pct)
        else:
            stop_loss = price * (1.0 + stop_loss_pct)
            take_profit = price * (1.0 - take_profit_pct)

        signal: Signal = {
            "symbol": symbol,
            "side": side,
            "strength": abs(ret),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }
        return signal if self.validate_signal(signal) else None

