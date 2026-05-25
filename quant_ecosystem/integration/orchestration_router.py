from quant_ecosystem.integration.service_mesh import (
    service_mesh,
)


class OrchestrationRouter:

    def route(
        self,
        service_name,
        method_name,
        *args,
        **kwargs,
    ):
        return service_mesh.call(
            service_name,
            method_name,
            *args,
            **kwargs,
        )


orchestration_router = (
    OrchestrationRouter()
)