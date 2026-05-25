from quant_ecosystem.integration.service_container import (
    service_container,
)


class ServiceRegistry:

    def register_batch(
        self,
        services,
    ):
        for name, svc in services.items():
            service_container.register(
                name,
                svc,
            )

    def registered(self):
        return dict(
            service_container._services
        )


service_registry = ServiceRegistry()