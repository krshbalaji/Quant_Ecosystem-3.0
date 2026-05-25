from quant_ecosystem.runtime import (
    lifecycle_manager,
)


class RuntimeEndpoint:

    def start(self):
        lifecycle_manager.start()
        return "RUNNING"

    def stop(self):
        lifecycle_manager.stop()
        return "STOPPED"

    def state(self):
        return lifecycle_manager.state()


runtime_endpoint = RuntimeEndpoint()