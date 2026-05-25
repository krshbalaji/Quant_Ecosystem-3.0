from quant_ecosystem.integration.service_container import (
    service_container,
)


class DependencyInjector:

    def inject(
        self,
        name,
    ):
        return service_container.resolve(
            name
        )


dependency_injector = (
    DependencyInjector()
)