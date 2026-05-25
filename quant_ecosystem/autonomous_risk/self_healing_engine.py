class SelfHealingEngine:

    def diagnose(
        self,
        risk_health,
        execution_alive=True,
        broker_connected=True,
    ):
        if not broker_connected:
            return "BROKER_RECOVERY"

        if not execution_alive:
            return "ENGINE_RECOVERY"

        if risk_health == "CRITICAL":
            return "RISK_CONTAINMENT"

        return "HEALTHY"

    def recover(
        self,
        diagnosis,
    ):
        mapping = {
            "BROKER_RECOVERY": "RECONNECT_BROKER",
            "ENGINE_RECOVERY": "RESTART_ENGINE",
            "RISK_CONTAINMENT": "REDUCE_EXPOSURE",
            "HEALTHY": "NO_ACTION",
        }

        return mapping[diagnosis]


self_healing_engine = (
    SelfHealingEngine()
)