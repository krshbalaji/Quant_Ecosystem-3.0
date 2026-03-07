"""Market event detector for event-driven signal triggering."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List


class MarketEventDetector:
    """Detects key market events from streaming snapshots."""

    def __init__(
        self,
        lookback: int = 30,
        volatility_spike_mult: float = 1.6,
        volume_spike_mult: float = 2.0,
        breakout_window: int = 20,
        order_imbalance_threshold: float = 0.35, **kwargs
    ):
        self.lookback = max(10, int(lookback))
        self.volatility_spike_mult = max(1.1, float(volatility_spike_mult))
        self.volume_spike_mult = max(1.2, float(volume_spike_mult))
        self.breakout_window = max(10, int(breakout_window))
        self.order_imbalance_threshold = max(0.05, min(0.95, float(order_imbalance_threshold)))
        self._history: Dict[str, Dict[str, Deque[float]]] = {}

    def ingest_snapshot(self, snapshot: Dict) -> List[Dict]:
        """Ingest one symbol snapshot and return detected events."""
        symbol = str(snapshot.get("symbol", "")).strip()
        if not symbol:
            return []
        state = self._history.setdefault(
            symbol,
            {
                "price": deque(maxlen=self.lookback + 5),
                "volume": deque(maxlen=self.lookback + 5),
                "volatility": deque(maxlen=self.lookback + 5),
                "imbalance": deque(maxlen=self.lookback + 5),
            },
        )

        price = self._f(snapshot.get("price"))
        volume = self._f(snapshot.get("volume"))
        volatility = self._f(snapshot.get("volatility"))
        bid_depth = self._f(snapshot.get("bid_depth", snapshot.get("depth_bid", 0.0)))
        ask_depth = self._f(snapshot.get("ask_depth", snapshot.get("depth_ask", 0.0)))
        imbalance = self._calc_imbalance(bid_depth, ask_depth)

        state["price"].append(price)
        state["volume"].append(volume)
        state["volatility"].append(volatility)
        state["imbalance"].append(imbalance)

        events = []
        if len(state["price"]) < 12:
            return events

        if self._is_volatility_spike(state["volatility"]):
            events.append(self._event(symbol, "volatility_spike", snapshot))
        if self._is_volume_spike(state["volume"]):
            events.append(self._event(symbol, "volume_spike", snapshot))
        breakout = self._price_breakout(state["price"])
        if breakout:
            events.append(self._event(symbol, breakout, snapshot))
        if abs(imbalance) >= self.order_imbalance_threshold:
            side = "buy_pressure" if imbalance > 0 else "sell_pressure"
            events.append(self._event(symbol, f"order_flow_imbalance_{side}", snapshot))

        return events

    def _is_volatility_spike(self, series: Deque[float]) -> bool:
        values = list(series)
        if len(values) < 10:
            return False
        latest = values[-1]
        base = values[:-1]
        mean = sum(base) / max(1, len(base))
        return latest > (mean * self.volatility_spike_mult)

    def _is_volume_spike(self, series: Deque[float]) -> bool:
        values = list(series)
        if len(values) < 10:
            return False
        latest = values[-1]
        base = values[:-1]
        mean = sum(base) / max(1, len(base))
        return latest > (mean * self.volume_spike_mult)

    def _price_breakout(self, series: Deque[float]) -> str:
        values = list(series)
        if len(values) < self.breakout_window + 1:
            return ""
        latest = values[-1]
        window = values[-self.breakout_window - 1:-1]
        if latest > max(window):
            return "price_breakout_up"
        if latest < min(window):
            return "price_breakout_down"
        return ""

    def _calc_imbalance(self, bid_depth: float, ask_depth: float) -> float:
        total = bid_depth + ask_depth
        if total <= 1e-9:
            return 0.0
        return (bid_depth - ask_depth) / total

    def _event(self, symbol: str, event_type: str, snapshot: Dict) -> Dict:
        return {
            "symbol": symbol,
            "event_type": event_type,
            "price": self._f(snapshot.get("price")),
            "volatility": self._f(snapshot.get("volatility")),
            "volume": self._f(snapshot.get("volume")),
            "snapshot": dict(snapshot),
        }

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

