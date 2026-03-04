"""Dynamic spread estimator for microstructure simulation."""

from __future__ import annotations

from datetime import datetime
from typing import Dict


class SpreadModel:
    """Estimates bid/ask spread from volatility, asset class, and time."""

    _BASE_SPREAD = {
        "stocks": 0.0008,
        "indices": 0.0006,
        "futures": 0.0007,
        "options": 0.0015,
        "forex": 0.0002,
        "crypto": 0.0012,
        "commodities": 0.0010,
    }

    def __init__(self, multiplier: float = 1.0):
        self.multiplier = max(0.1, float(multiplier))

    def estimate(self, volatility: float, asset_class: str = "stocks", timestamp: datetime | None = None) -> Dict:
        asset = str(asset_class or "stocks").strip().lower()
        base = float(self._BASE_SPREAD.get(asset, 0.0010))

        vol = max(0.0, float(volatility))
        vol_component = min(0.0030, vol * 0.0060)

        ts = timestamp or datetime.utcnow()
        hour = int(getattr(ts, "hour", 12))
        # Slightly wider spread around open/close windows.
        if hour in {3, 4, 9, 10, 15, 16}:
            tod_factor = 1.25
        elif hour in {0, 1, 2, 22, 23}:
            tod_factor = 1.15
        else:
            tod_factor = 1.0

        spread = (base + vol_component) * tod_factor * self.multiplier
        spread = max(0.00005, min(0.02, spread))

        return {
            "spread_pct": round(spread, 8),
            "base_spread_pct": round(base, 8),
            "vol_component_pct": round(vol_component, 8),
            "time_of_day_factor": tod_factor,
        }

