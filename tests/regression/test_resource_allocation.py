from quant_ecosystem.cognition.swarm import (
    ResourceAllocation,
)


def test_resource_allocation():

    allocation = ResourceAllocation(
        organism_id="alpha",
        resource_type="capital",
        approved_amount=10,
    )

    assert allocation.approved_amount == 10