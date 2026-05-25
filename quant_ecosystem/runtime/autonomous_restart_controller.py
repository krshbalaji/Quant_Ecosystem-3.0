from quant_ecosystem.runtime.runtime_supervisor import (
    runtime_supervisor,
)


class AutonomousRestartController:

    def recover(
        self,
        healthy=True,
    ):
        return runtime_supervisor.supervise(
            healthy=healthy
        )


autonomous_restart_controller = (
    AutonomousRestartController()
)