"""Market Pulse Engine."""

from __future__ import annotations

import asyncio
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.market_pulse.event_detector import PulseEventDetector


class MarketPulseEngine:
    """Continuously monitors market and publishes pulse events."""

    def __init__(self, event_detector: Optional[PulseEventDetector] = None, poll_interval_sec: float = 2.0):
        self.event_detector = event_detector or PulseEventDetector()
        self.poll_interval_sec = max(0.5, float(poll_interval_sec))
        self.last_events: List[Dict] = []

    def detect_events(self, snapshots: Iterable[Dict]) -> List[Dict]:
        events = self.event_detector.detect(snapshots)
        self.last_events = events
        return events

    def publish_events(
        self,
        events: Iterable[Dict],
        event_bus=None,
        signal_engine=None,
        strategy_selector=None,
        execution_engine=None,
        meta_strategy_brain=None,
    ) -> Dict:
        rows = list(events)
        published = {
            "count": len(rows),
            "bus": 0,
            "signal_engine": False,
            "strategy_selector": False,
            "execution_engine": False,
            "meta_strategy_brain": False,
        }

        # Event bus support: emit/publish/put_event
        if event_bus is not None:
            for event in rows:
                if self._push_event_bus(event_bus, event):
                    published["bus"] += 1

        if signal_engine is not None:
            try:
                setattr(signal_engine, "last_market_pulse_events", rows)
                published["signal_engine"] = True
            except Exception:
                pass

        if strategy_selector is not None:
            try:
                setattr(strategy_selector, "last_market_pulse_events", rows)
                published["strategy_selector"] = True
            except Exception:
                pass

        if execution_engine is not None:
            try:
                setattr(execution_engine, "last_market_pulse_events", rows)
                published["execution_engine"] = True
            except Exception:
                pass

        if meta_strategy_brain is not None:
            try:
                setattr(meta_strategy_brain, "last_market_pulse_events", rows)
                published["meta_strategy_brain"] = True
            except Exception:
                pass

        return published

    async def run_forever(
        self,
        snapshot_provider,
        event_bus=None,
        signal_engine=None,
        strategy_selector=None,
        execution_engine=None,
        meta_strategy_brain=None,
    ):
        """Run active pulse loop with async snapshot provider."""
        while True:
            try:
                snapshots = await snapshot_provider() if asyncio.iscoroutinefunction(snapshot_provider) else snapshot_provider()
                events = self.detect_events(snapshots or [])
                if events:
                    self.publish_events(
                        events=events,
                        event_bus=event_bus,
                        signal_engine=signal_engine,
                        strategy_selector=strategy_selector,
                        execution_engine=execution_engine,
                        meta_strategy_brain=meta_strategy_brain,
                    )
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval_sec)

    def _push_event_bus(self, bus, event: Dict) -> bool:
        try:
            if hasattr(bus, "emit"):
                bus.emit("MARKET_PULSE_EVENT", event)
                return True
            if hasattr(bus, "publish"):
                bus.publish("MARKET_PULSE_EVENT", event)
                return True
            if hasattr(bus, "put_event"):
                bus.put_event("MARKET_PULSE_EVENT", event)
                return True
        except Exception:
            return False
        return False

