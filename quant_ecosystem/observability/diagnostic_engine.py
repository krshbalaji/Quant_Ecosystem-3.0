class DiagnosticEngine:

    def diagnose(
        self,
        health,
        error_rate,
        broker_connected=True,
        execution_alive=True,
    ):
        if not broker_connected:
            return {
                "incident": "BROKER_OUTAGE",
                "severity": "CRITICAL",
            }

        if not execution_alive:
            return {
                "incident": "EXECUTION_FAILURE",
                "severity": "CRITICAL",
            }

        if health == "CRITICAL":
            return {
                "incident": "SYSTEM_STRESS",
                "severity": "HIGH",
            }

        if error_rate >= 5:
            return {
                "incident": "ERROR_SPIKE",
                "severity": "WATCH",
            }

        return {
            "incident": "HEALTHY",
            "severity": "NORMAL",
        }


diagnostic_engine = (
    DiagnosticEngine()
)