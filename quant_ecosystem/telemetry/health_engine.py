from datetime import datetime

from quant_ecosystem.telemetry.system_snapshot import (
    SystemSnapshot,
)

from quant_ecosystem.telemetry.telemetry_registry import (
    telemetry_registry,
)

from quant_ecosystem.regime.regime_state import (
    regime_state,
)


class HealthEngine:

    def capture(
        self,
        *,
        execution_latency_ms,
        broker_health_score,
        retry_pressure,
        queue_depth,
        capital_utilization,
        risk_utilization,
    ):

        snapshot = (
            SystemSnapshot(
                execution_latency_ms=(
                    execution_latency_ms
                ),

                broker_health_score=(
                    broker_health_score
                ),

                retry_pressure=(
                    retry_pressure
                ),

                queue_depth=queue_depth,

                capital_utilization=(
                    capital_utilization
                ),

                risk_utilization=(
                    risk_utilization
                ),

                regime_state=str(
                    regime_state.current().value
                ),

                timestamp=(
                    datetime.utcnow()
                    .isoformat()
                ),
            )
        )

        telemetry_registry.record(
            snapshot
        )

        return snapshot


health_engine = (
    HealthEngine()
)