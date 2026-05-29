from .federation_action import (
    FederationAction,
)
from .orchestration_request import (
    OrchestrationRequest,
)


class ExecutionRequestBuilder:

    def build(
        self,
        action: FederationAction,
    ) -> OrchestrationRequest:

        return OrchestrationRequest(
            request_id=action.action_id,
            workflow_type=(
                action.action_type
            ),
            payload=action.payload,
        )