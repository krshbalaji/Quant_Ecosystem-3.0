"""System health monitor for broker/connectivity/feed status."""

from __future__ import annotations

from typing import Dict, List


class SystemHealthMonitor:
    """Monitors critical service health and emits safety alerts."""

    def __init__(
        self,
        max_feed_latency_ms: float = 2500.0,
        max_api_errors_per_cycle: int = 5, **kwargs
    ):
        self.max_feed_latency_ms = float(max_feed_latency_ms)
        self.max_api_errors_per_cycle = int(max_api_errors_per_cycle)

    def evaluate(self, router, context: Dict | None = None) -> List[Dict]:
        ctx = dict(context or {})
        broker_router = getattr(router, "broker", None)
        broker = getattr(broker_router, "broker", None) if broker_router else None
        connected = bool(getattr(broker, "connected", False)) if broker else False

        feed_latency_ms = self._f(ctx.get("feed_latency_ms", 0.0))
        api_errors = int(ctx.get("api_errors", 0) or 0)

        alerts: List[Dict] = []
        if not connected:
            alerts.append(
                {
                    "monitor": "system_health_monitor",
                    "level": "EMERGENCY_STOP",
                    "reason": "Broker disconnected",
                    "metrics": {"broker_connected": False},
                }
            )
        if feed_latency_ms > self.max_feed_latency_ms:
            alerts.append(
                {
                    "monitor": "system_health_monitor",
                    "level": "RESTRICT",
                    "reason": (
                        f"Data feed latency {round(feed_latency_ms, 2)}ms > "
                        f"limit {round(self.max_feed_latency_ms, 2)}ms"
                    ),
                    "metrics": {"feed_latency_ms": round(feed_latency_ms, 3)},
                }
            )
        if api_errors > self.max_api_errors_per_cycle:
            alerts.append(
                {
                    "monitor": "system_health_monitor",
                    "level": "RESTRICT",
                    "reason": f"API errors {api_errors} > limit {self.max_api_errors_per_cycle}",
                    "metrics": {"api_errors": api_errors},
                }
            )
        return alerts

    def _f(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

