from quant_ecosystem.cognition.swarm import (
    FederationStrategyRegistry,
    StrategicObjective,
)


def test_strategy_registry():

    registry = (
        FederationStrategyRegistry()
    )

    registry.register(
        StrategicObjective(
            objective_id="OBJ1",
            description="Improve governance",
            priority=1,
        )
    )

    assert registry.count() == 1