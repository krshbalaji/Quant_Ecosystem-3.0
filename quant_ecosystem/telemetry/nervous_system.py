from quant_ecosystem.telemetry.telemetry_registry import (
    telemetry_registry,
)


class NervousSystem:

    def current_health(self):

        snapshot = (
            telemetry_registry.latest()
        )

        if snapshot is None:

            return {
                "status": "UNKNOWN"
            }

        stress_score = 0.0

        stress_score += (
            snapshot.execution_latency_ms
            / 1000.0
        )

        stress_score += (
            snapshot.retry_pressure
        )

        stress_score += (
            snapshot.capital_utilization
        )

        stress_score += (
            snapshot.risk_utilization
        )

        if stress_score >= 5:
            return {
                "status": "CRITICAL",
                "stress_score": (
                    stress_score
                ),
            }

        if stress_score >= 2:
            return {
                "status": "ELEVATED",
                "stress_score": (
                    stress_score
                ),
            }

        return {
            "status": "HEALTHY",
            "stress_score": (
                stress_score
            ),
        }


nervous_system = (
    NervousSystem()
)