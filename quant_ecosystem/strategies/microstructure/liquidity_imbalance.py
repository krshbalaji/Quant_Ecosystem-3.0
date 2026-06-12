from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class LiquidityImbalanceStrategy(BaseStrategy):
    """
    Simple liquidity imbalance proxy using volume changes.
    Buys when recent buying pressure is strong, sells on selling pressure.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 20,
            "threshold": 0.4,
            "stop_loss_pct": 0.8,
            "take_profit_pct": 1.5,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="liquidity_imbalance",
            name="Liquidity Imbalance",
            family="microstructure",
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

        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is None:
            return None

        vols = feature_engine.get_volume_series(symbol, timeframe="5m", lookback=lookback + 2)
        prices = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback + 2)
        if len(vols) < lookback + 1 or len(prices) < lookback + 1:
            return None

        vols_arr = np.array(vols[-lookback:], dtype=float)
        px_arr = np.array(prices[-lookback:], dtype=float)
        vol_norm = vols_arr / (vols_arr.mean() + 1e-9)
        price_change = np.sign(np.diff(px_arr, prepend=px_arr[0]))
        pressure = float(np.mean(vol_norm * price_change))

        threshold_value = self.params.get("threshold", 0.4)

        thresh = float(
            threshold_value
            if isinstance(threshold_value, (int, float))
            else 0.4
        )
        side: Optional[str] = None
        if pressure > thresh:
            side = "BUY"
        elif pressure < -thresh:
            side = "SELL"

        if not side:
            return None

        price = float(px_arr[-1])
        sl_value = self.params.get("stop_loss_pct", 0.8)
        stop_loss_pct = float(
            sl_value
            if isinstance(sl_value, (int, float))
            else 0.8
        ) / 100.0

        tp_value = self.params.get("take_profit_pct", 1.5)
        take_profit_pct = float(
            tp_value
            if isinstance(tp_value, (int, float))
            else 1.5
        ) / 100.0

        if side == "BUY":
            stop_loss = price * (1.0 - stop_loss_pct)
            take_profit = price * (1.0 + take_profit_pct)
        else:
            stop_loss = price * (1.0 + stop_loss_pct)
            take_profit = price * (1.0 - take_profit_pct)

        signal: Signal = {
            "symbol": symbol,
            "side": side,
            "strength": abs(pressure),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }
        return signal if self.validate_signal(signal) else None

