from .capability_health import (
    CapabilityHealth,
)
from .federation_capability_registry import (
    FederationCapabilityRegistry,
)


class FederationCapabilityMonitor:

    def evaluate(
        self,
        registry: FederationCapabilityRegistry,
    ):

        results = []

        for capability in (
            registry._capabilities.values()
        ):
            results.append(
                CapabilityHealth(
                    capability_id=(
                        capability.capability_id
                    ),
                    healthy=capability.active,
                )
            )

        return results