from .qe3_federation_adapter_registry import (
    QE3FederationAdapterRegistry,
)
from .subsystem_adapter_request import (
    SubsystemAdapterRequest,
)
from .subsystem_adapter_result import (
    SubsystemAdapterResult,
)


class QE3FederationAdapterEngine:

    def __init__(
        self,
        registry: QE3FederationAdapterRegistry,
    ):
        self.registry = registry

    def submit(
        self,
        request: SubsystemAdapterRequest,
    ) -> SubsystemAdapterResult:

        accepted = (
            self.registry.enabled(
                request.subsystem_name
            )
        )

        return SubsystemAdapterResult(
            request_id=request.request_id,
            accepted=accepted,
            subsystem_name=(
                request.subsystem_name
            ),
        )