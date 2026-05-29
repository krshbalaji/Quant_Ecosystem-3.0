from .execution_authorization_engine import (
    ExecutionAuthorizationEngine,
)
from .execution_authorization import (
    ExecutionAuthorization,
)
from .execution_policy import ExecutionPolicy
from .execution_request import ExecutionRequest


class FederationExecutionGate:

    def __init__(self):
        self.engine = ExecutionAuthorizationEngine()

    def evaluate(
        self,
        request: ExecutionRequest,
        policy: ExecutionPolicy,
    ) -> ExecutionAuthorization:

        return self.engine.authorize(
            request,
            policy,
        )