from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class VolatilityExpansionStrategy(BaseStrategy):
    """
    Volatility expansion strategy.
    Looks for sudden increases in realised volatility and trades in the
    direction of the expansion.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None):
        default_params: Dict[str, object] = {
            "lookback": 40,
            "expansion_factor": 1.5,
            "stop_loss_pct": 1.2,
            "take_profit_pct": 2.5,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="volatility_expansion",
            name="Volatility Expansion",
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
        lookback = int(max(10, float(self.params.get("lookback", 40))))

        feature_engine = getattr(market_data, "feature_engine", None)
        if feature_engine is not None:
            series = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback + 10)
        else:
            series = market_data.get_series(symbol=symbol, timeframe="5m", lookback=lookback + 10)
        if len(series) < lookback + 5:
            return None

        arr = np.array(series, dtype=float)
        rets = np.diff(arr) / np.where(arr[:-1] == 0, 1.0, arr[:-1])
        if len(rets) < lookback + 5:
            return None

        recent = rets[-lookback:]
        prior = rets[-(2 * lookback) : -lookback]
        if len(prior) < lookback:
            return None

        recent_vol = float(np.std(recent))
        prior_vol = float(np.std(prior))
        if prior_vol <= 0:
            return None

        factor = recent_vol / prior_vol
        expansion_threshold = float(self.params.get("expansion_factor", 1.5))
        if factor < expansion_threshold:
            return None

        # Trade in the direction of the recent move
        direction = np.sign(recent.mean())
        if direction == 0:
            return None
        side = "BUY" if direction > 0 else "SELL"

        price = float(arr[-1])
        stop_loss_pct = float(self.params.get("stop_loss_pct", 1.2)) / 100.0
        take_profit_pct = float(self.params.get("take_profit_pct", 2.5)) / 100.0

        if side == "BUY":
            stop_loss = price * (1.0 - stop_loss_pct)
            take_profit = price * (1.0 + take_profit_pct)
        else:
            stop_loss = price * (1.0 + stop_loss_pct)
            take_profit = price * (1.0 - take_profit_pct)

        signal: Signal = {
            "symbol": symbol,
            "side": side,
            "strength": abs(factor),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }
        return signal if self.validate_signal(signal) else None

