from quant_ecosystem.autonomous_risk.self_healing_engine import (
    self_healing_engine,
)


class AutonomousControls:

    def kill_switch(
        self,
        risk_health,
    ):
        return risk_health == "CRITICAL"

    def can_resume(
        self,
        risk_health,
        broker_connected=True,
        execution_alive=True,
    ):
        return (
            risk_health != "CRITICAL"
            and broker_connected
            and execution_alive
        )

    def evaluate(
        self,
        risk_health,
        execution_alive=True,
        broker_connected=True,
    ):
        diagnosis = (
            self_healing_engine
            .diagnose(
                risk_health,
                execution_alive,
                broker_connected,
            )
        )

        return {
            "kill_switch": self.kill_switch(
                risk_health
            ),
            "diagnosis": diagnosis,
            "recovery_action": (
                self_healing_engine
                .recover(diagnosis)
            ),
            "can_resume": self.can_resume(
                risk_health,
                broker_connected,
                execution_alive,
            ),
        }


autonomous_controls = (
    AutonomousControls()
)