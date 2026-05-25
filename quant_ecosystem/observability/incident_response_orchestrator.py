from quant_ecosystem.observability.diagnostic_engine import (
    diagnostic_engine,
)


class IncidentResponseOrchestrator:

    def response_plan(
        self,
        incident,
    ):
        mapping = {
            "BROKER_OUTAGE": "FAILOVER_OR_RECONNECT",
            "EXECUTION_FAILURE": "RESTART_EXECUTION",
            "SYSTEM_STRESS": "THROTTLE_LOAD",
            "ERROR_SPIKE": "INVESTIGATE_ERRORS",
            "HEALTHY": "NO_ACTION",
        }

        return mapping[incident]

    def evaluate(
        self,
        health,
        error_rate,
        broker_connected=True,
        execution_alive=True,
    ):
        diagnosis = (
            diagnostic_engine
            .diagnose(
                health,
                error_rate,
                broker_connected,
                execution_alive,
            )
        )

        return {
            "diagnosis": diagnosis,
            "action": self.response_plan(
                diagnosis["incident"]
            ),
        }


incident_response_orchestrator = (
    IncidentResponseOrchestrator()
)