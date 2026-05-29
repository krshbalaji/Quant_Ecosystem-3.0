from quant_ecosystem.cognition.swarm import (
    FederationStrategyEngine,
    FederationStrategyRegistry,
    StrategicObjective,
)


def test_strategy_engine():

    registry = (
        FederationStrategyRegistry()
    )

    registry.register(
        StrategicObjective(
            objective_id="OBJ1",
            description="Improve readiness",
            priority=1,
        )
    )

    plan = (
        FederationStrategyEngine()
        .generate_plan(
            registry
        )
    )

    assert plan.objective_count == 1