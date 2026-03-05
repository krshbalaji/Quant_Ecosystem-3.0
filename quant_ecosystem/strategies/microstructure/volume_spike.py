from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class VolumeSpikeStrategy(BaseStrategy):
    """
    Volume spike strategy.
    Detects abnormal increases in per-bar volume relative to recent history.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None):
        default_params: Dict[str, object] = {
            "lookback": 30,
            "spike_factor": 2.0,
            "stop_loss_pct": 0.8,
            "take_profit_pct": 1.5,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="volume_spike",
            name="Volume Spike",
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
        lookback = int(max(10, float(self.params.get("lookback", 30))))

        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is None:
            return None

        vols = feature_engine.get_volume_series(symbol, timeframe="5m", lookback=lookback + 1)
        closes = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback + 1)
        if len(vols) < lookback + 1 or len(closes) < lookback + 1:
            return None

        arr_vol = np.array(vols, dtype=float)
        arr_px = np.array(closes, dtype=float)
        base = arr_vol[-(lookback + 1) : -1]
        current = arr_vol[-1]
        mean = float(base.mean())
        if mean <= 0:
            return None

        spike_factor = current / mean
        threshold = float(self.params.get("spike_factor", 2.0))
        if spike_factor < threshold:
            return None

        # Direction proxy: last price move
        delta = arr_px[-1] - arr_px[-2]
        if delta == 0:
            return None
        side = "BUY" if delta > 0 else "SELL"

        price = float(arr_px[-1])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 0.8)) / 100.0
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
            "strength": float(spike_factor),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }
        return signal if self.validate_signal(signal) else None

