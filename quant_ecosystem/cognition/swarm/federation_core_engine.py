from .federation_health_check import (
    FederationHealthCheck,
)
from .federation_registry import (
    FederationRegistry,
)


class FederationCoreEngine:

    def evaluate(
        self,
        registry: FederationRegistry,
    ) -> FederationHealthCheck:

        return FederationHealthCheck(
            healthy=True,
            component_count=registry.count(),
        )