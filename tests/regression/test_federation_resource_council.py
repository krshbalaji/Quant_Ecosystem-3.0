from quant_ecosystem.cognition.swarm import (
    AllocationPolicy,
    FederationResourceCouncil,
    ResourceRequest,
)


def test_resource_council():

    council = FederationResourceCouncil()

    allocation = council.evaluate_request(
        ResourceRequest(
            organism_id="alpha",
            resource_type="risk_budget",
            requested_amount=40,
        ),
        AllocationPolicy(
            resource_type="risk_budget",
            maximum_allocation=50,
        ),
    )

    assert allocation.approved_amount == 40