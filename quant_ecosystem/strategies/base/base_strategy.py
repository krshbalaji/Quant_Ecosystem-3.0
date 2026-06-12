from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


Signal = Dict[str, object]


@dataclass
class BaseStrategy(ABC):
    """
    Institutional base contract for all strategies.
    """

    id: str
    name: str
    family: str
    params: Dict[str, object] = field(default_factory=dict)
    required_timeframes: List[str] = field(default_factory=lambda: ["5m"])
    required_symbols: List[str] = field(default_factory=list)

    def validate_signal(self, signal: Optional[Signal]) -> bool:
        """
        Basic structural validation for generated signals.
        """
        if not signal:
            return False

        required = {"symbol", "side", "strength", "stop_loss", "take_profit", "meta"}
        if not required.issubset(signal.keys()):
            return False

        side = str(signal.get("side", "")).upper()
        if side not in {"BUY", "SELL"}:
            return False

        try:
            strength = signal.get("strength", 0.0)
            stop_loss = signal.get("stop_loss", 0.0)
            take_profit = signal.get("take_profit", 0.0)

            float(
                strength
                if isinstance(strength, (int, float, str))
                else 0.0
            )

            float(
                stop_loss
                if isinstance(stop_loss, (int, float, str))
                else 0.0
            )

            float(
                take_profit
                if isinstance(take_profit, (int, float, str))
                else 0.0
            )

        except (TypeError, ValueError):
            return False

        return True

    @abstractmethod
    def generate_signal(self, market_data) -> Optional[Signal]:
        """
        Produce a trading signal given the latest market data snapshot.
        """

    def on_fill(self, fill_event: Dict[str, object]) -> None:
        """
        Lifecycle hook invoked by the execution layer after an order fill.
        """
        return None

    def on_bar_close(self, symbol: str, timeframe: str, candle: Dict[str, object]) -> None:
        """
        Lifecycle hook invoked on each completed bar in backtests or live trading.
        """
        return None

