"""Market pulse event detector."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from quant_ecosystem.market_pulse.breakout_monitor import BreakoutMonitor
from quant_ecosystem.market_pulse.liquidity_monitor import LiquidityMonitor
from quant_ecosystem.market_pulse.volatility_monitor import VolatilityMonitor
from quant_ecosystem.market_pulse.volume_monitor import VolumeMonitor


class PulseEventDetector:
    """Combines monitor outputs and emits normalized events."""

    def __init__(
        self,
        volatility_monitor: Optional[VolatilityMonitor] = None,
        volume_monitor: Optional[VolumeMonitor] = None,
        breakout_monitor: Optional[BreakoutMonitor] = None,
        liquidity_monitor: Optional[LiquidityMonitor] = None,
        min_strength: float = 0.2, **kwargs
    ):
        self.volatility_monitor = volatility_monitor or VolatilityMonitor()
        self.volume_monitor = volume_monitor or VolumeMonitor()
        self.breakout_monitor = breakout_monitor or BreakoutMonitor()
        self.liquidity_monitor = liquidity_monitor or LiquidityMonitor()
        self.min_strength = max(0.0, min(1.0, float(min_strength)))

    def detect(self, snapshots: Iterable[Dict]) -> List[Dict]:
        events: List[Dict] = []
        for snap in snapshots:
            symbol = str(snap.get("symbol", "")).strip()
            if not symbol:
                continue

            results = [
                self.volatility_monitor.evaluate(snap),
                self.volume_monitor.evaluate(snap),
                self.breakout_monitor.evaluate(snap),
                self.liquidity_monitor.evaluate(snap),
            ]
            for res in results:
                if not res.get("triggered", False):
                    continue
                strength = float(res.get("strength", 0.0))
                if strength < self.min_strength:
                    continue
                events.append(
                    {
                        "event_type": str(res.get("event_type", "UNKNOWN")).upper(),
                        "symbol": symbol,
                        "strength": round(strength, 6),
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "details": dict(res),
                        "snapshot": dict(snap),
                    }
                )
        return events
