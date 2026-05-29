from quant_ecosystem.cognition.swarm import (
    AllocationPolicy,
    CapitalGovernanceEngine,
    ResourceRequest,
)


def test_allocation_respects_policy():

    engine = CapitalGovernanceEngine()

    allocation = engine.allocate(
        ResourceRequest(
            organism_id="alpha",
            resource_type="capital",
            requested_amount=150,
        ),
        AllocationPolicy(
            resource_type="capital",
            maximum_allocation=100,
        ),
    )

    assert allocation.approved_amount == 100