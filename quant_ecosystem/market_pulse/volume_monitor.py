"""Volume monitor for market pulse."""

from __future__ import annotations

from typing import Dict, List


class VolumeMonitor:
    """Detects abnormal trading activity."""

    def __init__(self, volume_multiplier: float = 2.0, **kwargs):
        self.volume_multiplier = max(1.1, float(volume_multiplier))

    def evaluate(self, snapshot: Dict) -> Dict:
        volume = self._series(snapshot.get("volume", []))
        if len(volume) < 20:
            return {"triggered": False, "event_type": "VOLUME_SPIKE", "strength": 0.0}

        current = volume[-1]
        mean = sum(volume[:-1]) / max(1, len(volume) - 1)
        triggered = mean > 1e-9 and current > (mean * self.volume_multiplier)
        strength = 0.0
        if mean > 1e-9:
            strength = min(1.0, max(0.0, (current / mean - 1.0) / self.volume_multiplier))
        return {
            "triggered": bool(triggered),
            "event_type": "VOLUME_SPIKE",
            "strength": round(strength, 6),
            "volume_current": round(current, 6),
            "volume_mean": round(mean, 6),
        }

    def _series(self, values) -> List[float]:
        out = []
        for v in values or []:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                continue
        return out

