from .federation_action import (
    FederationAction,
)
from .federation_handoff import (
    FederationHandoff,
)
from .federation_integration_registry import (
    FederationIntegrationRegistry,
)


class FederationIntegrationEngine:

    def __init__(
        self,
        registry: FederationIntegrationRegistry,
    ):
        self.registry = registry

    def handoff(
        self,
        action: FederationAction,
        target_system: str,
    ) -> FederationHandoff:

        accepted = self.registry.enabled(
            target_system
        )

        return FederationHandoff(
            action_id=action.action_id,
            target_system=target_system,
            accepted=accepted,
        )