from quant_ecosystem.runtime.lifecycle_manager import (
    lifecycle_manager,
)


class RuntimeSupervisor:

    def supervise(
        self,
        healthy=True,
    ):
        if not healthy:
            lifecycle_manager.restart()
            return "RESTARTED"

        return "STABLE"


runtime_supervisor = RuntimeSupervisor()