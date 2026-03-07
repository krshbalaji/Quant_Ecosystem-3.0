from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class CrossSectionMomentumStrategy(BaseStrategy):
    """
    Cross-sectional momentum strategy.
    Ranks symbols by recent returns and generates a signal on the top-ranked symbol.
    """

    def __init__(self, params: Optional[Dict[str, object]] = None, **kwargs):
        default_params: Dict[str, object] = {
            "lookback": 20,
            "top_n": 1,
            "stop_loss_pct": 1.0,
            "take_profit_pct": 2.0,
        }
        merged = {**default_params, **(params or {})}
        super().__init__(
            id="cross_section_momentum",
            name="Cross-Section Momentum",
            family="momentum",
            params=merged,
            required_timeframes=["5m"],
            required_symbols=[],
        )

    def _rank_symbols(self, market_data) -> List[Tuple[str, float]]:
        symbols = self.required_symbols or list(getattr(market_data, "symbols", []) or [])
        lookback = int(max(5, float(self.params.get("lookback", 20))))
        ranks: List[Tuple[str, float]] = []

        feature_engine = getattr(market_data, "feature_engine", None)

        for symbol in symbols:
            if feature_engine is not None:
                series = feature_engine.get_close_series(symbol, timeframe="5m", lookback=lookback + 1)
            else:
                series = market_data.get_series(symbol=symbol, timeframe="5m", lookback=lookback + 1)
            if len(series) < lookback + 1:
                continue
            recent = np.array(series[-lookback:], dtype=float)
            if recent[0] == 0:
                continue
            ret = (recent[-1] - recent[0]) / abs(recent[0])
            ranks.append((symbol, float(ret)))
        ranks.sort(key=lambda x: x[1], reverse=True)
        return ranks

    def generate_signal(self, market_data) -> Optional[Signal]:
        ranked = self._rank_symbols(market_data)
        if not ranked:
            return None

        symbol, momentum = ranked[0]
        price = getattr(market_data, "get_latest_price", lambda s: None)(symbol)
        if price is None:
            series = (
                getattr(market_data, "feature_engine", None)
                or market_data
            ).get_series(symbol=symbol, timeframe="5m", lookback=1)
            if not series:
                return None
            price = float(series[-1])

        side = "BUY" if momentum > 0 else "SELL"

        stop_loss_pct = float(self.params.get("stop_loss_pct", 1.0)) / 100.0
        take_profit_pct = float(self.params.get("take_profit_pct", 2.0)) / 100.0

        if side == "BUY":
            stop_loss = price * (1.0 - stop_loss_pct)
            take_profit = price * (1.0 + take_profit_pct)
        else:
            stop_loss = price * (1.0 + stop_loss_pct)
            take_profit = price * (1.0 - take_profit_pct)

        signal: Signal = {
            "symbol": symbol,
            "side": side,
            "strength": abs(momentum),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "meta": {
                "strategy_id": self.id,
                "family": self.family,
            },
        }
        return signal if self.validate_signal(signal) else None

