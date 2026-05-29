from .execution_adapter_registry import (
    ExecutionAdapterRegistry,
)
from .router_execution_request import (
    RouterExecutionRequest,
)
from .router_execution_result import (
    RouterExecutionResult,
)


class FederationExecutionRouterAdapter:

    def __init__(
        self,
        registry: ExecutionAdapterRegistry,
    ):
        self.registry = registry

    def route(
        self,
        request: RouterExecutionRequest,
        adapter_id: str,
    ) -> RouterExecutionResult:

        accepted = self.registry.enabled(
            adapter_id
        )

        return RouterExecutionResult(
            request_id=request.request_id,
            accepted=accepted,
            adapter_id=adapter_id,
        )