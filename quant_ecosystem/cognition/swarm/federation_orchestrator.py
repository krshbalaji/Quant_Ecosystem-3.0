from .orchestration_registry import (
    OrchestrationRegistry,
)
from .orchestration_request import (
    OrchestrationRequest,
)
from .orchestration_result import (
    OrchestrationResult,
)


class FederationOrchestrator:

    def __init__(
        self,
        registry: OrchestrationRegistry,
    ):
        self.registry = registry

    def execute(
        self,
        request: OrchestrationRequest,
    ) -> OrchestrationResult:

        completed = (
            self.registry.enabled_count()
        )

        return OrchestrationResult(
            request_id=request.request_id,
            successful=True,
            stages_completed=completed,
        )