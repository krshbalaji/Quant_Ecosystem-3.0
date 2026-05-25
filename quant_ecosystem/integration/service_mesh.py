from quant_ecosystem.integration.service_container import (
    service_container,
)


class ServiceMesh:

    def call(
        self,
        service_name,
        method_name,
        *args,
        **kwargs,
    ):
        svc = service_container.resolve(
            service_name
        )

        if svc is None:
            raise ValueError(
                f"Service not found: {service_name}"
            )

        method = getattr(
            svc,
            method_name,
        )

        return method(
            *args,
            **kwargs,
        )


service_mesh = ServiceMesh()