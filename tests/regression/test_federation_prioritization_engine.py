from quant_ecosystem.cognition.swarm import (
    FederationPrioritizationEngine,
    FederationPrioritizationRegistry,
    StrategicObjective,
)


def test_prioritization_engine():

    registry = (
        FederationPrioritizationRegistry()
    )

    registry.register(
        StrategicObjective(
            objective_id="OBJ1",
            description="Improve readiness",
            priority=1,
        )
    )

    report = (
        FederationPrioritizationEngine()
        .prioritize(
            registry
        )
    )

    assert report.objective_count == 1
    assert (
        report.objectives[0]
        .priority_rank
        == 1
    )