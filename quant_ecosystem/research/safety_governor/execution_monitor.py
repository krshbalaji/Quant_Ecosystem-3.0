"""Execution monitor for trade pace, rejections, and slippage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List


class ExecutionMonitor:
    """Detects abnormal execution behavior patterns."""

    def __init__(
        self,
        trades_per_minute_limit: int = 30,
        rejection_rate_limit: float = 0.5,
        slippage_bps_limit: float = 12.0, **kwargs
    ):
        self.trades_per_minute_limit = int(trades_per_minute_limit)
        self.rejection_rate_limit = float(rejection_rate_limit)
        self.slippage_bps_limit = float(slippage_bps_limit)

    def evaluate(self, router, context: Dict | None = None) -> List[Dict]:
        ctx = dict(context or {})
        state = getattr(router, "state", None)
        history = list(getattr(state, "trade_history", []) or []) if state else []
        now = datetime.now(timezone.utc)
        one_min_ago = now - timedelta(minutes=1)

        recent = []
        for row in reversed(history[-300:]):
            ts = self._parse_ts(row.get("timestamp"))
            if ts and ts >= one_min_ago:
                recent.append(row)
        trades_per_minute = len(recent)

        cycle_stats = dict(ctx.get("cycle_stats", {}) or {})
        accepted = self._f(cycle_stats.get("accepted_trades", 0.0))
        rejected = self._f(cycle_stats.get("rejected_signals", 0.0))
        total_attempts = accepted + rejected
        min_samples = max(
            1,
            int(getattr(getattr(router, "config", None), "safety_governor_min_rejection_samples", 8)),
        )
        rejection_rate = (rejected / total_attempts) if total_attempts > 0 else 0.0

        slip_values = [
            self._f(row.get("slippage_bps", 0.0))
            for row in history[-80:]
            if row.get("status", "FILLED") != "SKIP"
        ]
        avg_slippage = (sum(slip_values) / len(slip_values)) if slip_values else 0.0

        alerts: List[Dict] = []
        if trades_per_minute > self.trades_per_minute_limit:
            alerts.append(
                {
                    "monitor": "execution_monitor",
                    "level": "RESTRICT",
                    "reason": (
                        f"Trade frequency {trades_per_minute}/min > limit "
                        f"{self.trades_per_minute_limit}/min"
                    ),
                    "metrics": {"trades_per_minute": trades_per_minute},
                }
            )
        if total_attempts >= min_samples and rejection_rate > self.rejection_rate_limit:
            alerts.append(
                {
                    "monitor": "execution_monitor",
                    "level": "THROTTLE",
                    "reason": (
                        f"Order rejection rate {round(rejection_rate * 100.0, 2)}% "
                        f"> limit {round(self.rejection_rate_limit * 100.0, 2)}%"
                    ),
                    "metrics": {
                        "rejection_rate": round(rejection_rate, 6),
                        "rejection_samples": int(total_attempts),
                        "min_rejection_samples": int(min_samples),
                    },
                }
            )
        if avg_slippage > self.slippage_bps_limit:
            alerts.append(
                {
                    "monitor": "execution_monitor",
                    "level": "THROTTLE",
                    "reason": (
                        f"Average slippage {round(avg_slippage, 2)} bps > "
                        f"limit {round(self.slippage_bps_limit, 2)} bps"
                    ),
                    "metrics": {"avg_slippage_bps": round(avg_slippage, 6)},
                }
            )
        return alerts

    def _parse_ts(self, value):
        if not value:
            return None
        try:
            txt = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
