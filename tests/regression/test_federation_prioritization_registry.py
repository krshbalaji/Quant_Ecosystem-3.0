from quant_ecosystem.cognition.swarm import (
    FederationPrioritizationRegistry,
    StrategicObjective,
)


def test_prioritization_registry():

    registry = (
        FederationPrioritizationRegistry()
    )

    registry.register(
        StrategicObjective(
            objective_id="OBJ1",
            description="Improve governance",
            priority=1,
        )
    )

    assert registry.count() == 1