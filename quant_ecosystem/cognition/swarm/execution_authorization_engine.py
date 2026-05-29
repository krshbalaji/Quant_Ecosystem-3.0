from .execution_authorization import (
    ExecutionAuthorization,
)
from .execution_policy import ExecutionPolicy
from .execution_request import ExecutionRequest


class ExecutionAuthorizationEngine:

    def authorize(
        self,
        request: ExecutionRequest,
        policy: ExecutionPolicy,
    ) -> ExecutionAuthorization:

        if not policy.active:
            return ExecutionAuthorization(
                organism_id=request.organism_id,
                execution_type=request.execution_type,
                authorized=False,
                approved_amount=0.0,
            )

        approved_amount = min(
            request.requested_amount,
            policy.maximum_authorization,
        )

        return ExecutionAuthorization(
            organism_id=request.organism_id,
            execution_type=request.execution_type,
            authorized=approved_amount > 0,
            approved_amount=approved_amount,
        )