from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class ATRBreakoutStrategy(BaseStrategy):
    """
    ATR-based volatility breakout strategy.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
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

    @staticmethod
    def _to_float(
        value: object,
        default: float,
    ) -> float:
        return float(value) if isinstance(value, (int, float)) else default    
        
        length = int(max(5, _to_float(self.params.get("atr_length"), 14.0)))

        mult = _to_float(self.params.get("atr_mult"), 2.0)

        sl_mult = _to_float(self.params.get("stop_loss_mult"), 1.0)

        tp_mult = _to_float(self.params.get("take_profit_mult"), 2.0)
        
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

