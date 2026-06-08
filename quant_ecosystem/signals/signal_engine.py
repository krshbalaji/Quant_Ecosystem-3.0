from __future__ import annotations

from typing import Any, Dict, List, Optional

from quant_ecosystem.strategies.base.base_strategy import BaseStrategy, Signal


class SignalEngine:
    """
    Institutional signal engine.

    Pulls strategies from StrategyRegistry, calls generate_signal on each,
    validates via BaseStrategy.validate_signal, and returns a standardised
    list of signal intents. No orders are created here.
    """

    def __init__(self, strategy_registry, market_data, **kwargs):
        self.strategy_registry = strategy_registry
        self.market_data = market_data

    def _iter_strategies(self) -> List[BaseStrategy]:
        if not hasattr(self.strategy_registry, "get_all"):
            return []
        raw = self.strategy_registry.get_all()
        if isinstance(raw, dict):
            return list(raw.values())
        return list(raw or [])

    def generate_signals(self) -> List[Dict]:
        signals: List[Dict] = []

        for strategy in self._iter_strategies():
            if not isinstance(strategy, BaseStrategy):
                continue

            try:
                sig: Optional[Signal] = strategy.generate_signal(
                    self.market_data
                )
            except Exception:
                continue

            if sig is None:
                continue

            if not strategy.validate_signal(sig):
                continue

            strength = sig.get("strength", 1.0)
            stop_loss = sig.get("stop_loss")
            take_profit = sig.get("take_profit")
            meta = sig.get("meta", {})

            payload: Dict[str, Any] = {
                "strategy_id": strategy.id,
                "symbol": str(sig["symbol"]),
                "side": str(sig["side"]),
                "strength": float(str(strength)),
                "stop_loss": (
                    float(str(stop_loss))
                    if stop_loss is not None
                    else None
                ),
                "take_profit": (
                    float(str(take_profit))
                    if take_profit is not None
                    else None
                ),
                "meta": meta if isinstance(meta, dict) else {},
            }

            signals.append(payload)

        return signals