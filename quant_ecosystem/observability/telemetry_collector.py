from quant_ecosystem.observability.metrics_registry import (
    metrics_registry,
)

from quant_ecosystem.observability.runtime_health_engine import (
    runtime_health_engine,
)


class TelemetryCollector:

    def record_event(
        self,
        event_name,
    ):
        metrics_registry.increment(event_name)

    def runtime_snapshot(
        self,
        cpu_pct,
        memory_pct,
        error_rate,
    ):
        return {
            "cpu_pct": cpu_pct,
            "memory_pct": memory_pct,
            "error_rate": error_rate,
            "health": (
                runtime_health_engine.classify(
                    cpu_pct,
                    memory_pct,
                    error_rate,
                )
            ),
            "metrics": (
                metrics_registry.snapshot()
            ),
        }


telemetry_collector = (
    TelemetryCollector()
)