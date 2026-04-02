"""Timed or regime-change based rebalance trigger manager."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


class RebalanceManager:
    """Determines when rebalancing should be executed."""

    def __init__(self, interval_minutes: int = 30, **kwargs):
        self.interval = timedelta(minutes=max(1, int(interval_minutes)))
        self.last_rebalance_at: Optional[datetime] = None
        self.last_regime: Optional[str] = None

    def should_rebalance(self, regime: str, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        regime_changed = (self.last_regime is not None) and (str(regime).upper() != str(self.last_regime).upper())
        due_time = (
            self.last_rebalance_at is None
            or (now - self.last_rebalance_at) >= self.interval
        )
        return bool(regime_changed or due_time)

    def mark_rebalanced(self, regime: str, when: Optional[datetime] = None) -> None:
        self.last_rebalance_at = when or datetime.now(timezone.utc)
        self.last_regime = str(regime).upper()

