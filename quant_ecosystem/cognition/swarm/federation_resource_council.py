from .allocation_policy import AllocationPolicy
from .capital_governance_engine import (
    CapitalGovernanceEngine,
)
from .resource_allocation import ResourceAllocation
from .resource_request import ResourceRequest


class FederationResourceCouncil:

    def __init__(self):
        self.engine = CapitalGovernanceEngine()

    def evaluate_request(
        self,
        request: ResourceRequest,
        policy: AllocationPolicy,
    ) -> ResourceAllocation:

        return self.engine.allocate(
            request,
            policy,
        )