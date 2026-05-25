from quant_ecosystem.integration.service_registry import (
    service_registry,
)


class CompositionEngine:

    def compose(
        self,
        services,
    ):
        service_registry.register_batch(
            services
        )

        return True


composition_engine = (
    CompositionEngine()
)