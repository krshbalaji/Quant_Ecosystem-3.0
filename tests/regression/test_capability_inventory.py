from quant_ecosystem.cognition.swarm import (
    CapabilityInventory,
)


def test_inventory_model():

    inventory = CapabilityInventory(
        total_capabilities=3,
        active_capabilities=2,
    )

    assert inventory.total_capabilities == 3