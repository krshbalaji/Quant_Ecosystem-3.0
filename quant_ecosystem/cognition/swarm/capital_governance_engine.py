from .allocation_policy import AllocationPolicy
from .resource_allocation import ResourceAllocation
from .resource_request import ResourceRequest


class CapitalGovernanceEngine:

    def allocate(
        self,
        request: ResourceRequest,
        policy: AllocationPolicy,
    ) -> ResourceAllocation:

        approved = min(
            request.requested_amount,
            policy.maximum_allocation,
        )

        return ResourceAllocation(
            organism_id=request.organism_id,
            resource_type=request.resource_type,
            approved_amount=approved,
        )