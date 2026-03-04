"""Event router for module-targeted dispatch."""

from __future__ import annotations

from typing import Dict, List


class EventRouter:
    """Maps event types to handler method names."""

    def __init__(self):
        self.routes: Dict[str, List[str]] = {
            "VOLATILITY_SPIKE": ["handle_volatility_spike"],
            "PRICE_BREAKOUT": ["handle_breakout"],
            "TREND_SHIFT": ["handle_breakout"],
            "VOLUME_SPIKE": ["handle_volume_event"],
            "LIQUIDITY_DROP": ["handle_liquidity_drop"],
        }

    def add_route(self, event_type: str, handler_name: str) -> None:
        key = str(event_type or "UNKNOWN").upper()
        self.routes.setdefault(key, [])
        if handler_name not in self.routes[key]:
            self.routes[key].append(handler_name)

    def route(self, event: Dict) -> List[str]:
        key = str(event.get("event_type", "UNKNOWN")).upper()
        return list(self.routes.get(key, []))

