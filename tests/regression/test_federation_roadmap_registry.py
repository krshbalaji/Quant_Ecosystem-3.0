from quant_ecosystem.cognition.swarm import (
    FederationRoadmapRegistry,
    PrioritizedObjective,
)


def test_roadmap_registry():

    registry = (
        FederationRoadmapRegistry()
    )

    registry.register(
        PrioritizedObjective(
            objective_id="OBJ1",
            priority_rank=1,
            score=100.0,
        )
    )

    assert (
        len(
            registry.objectives()
        )
        == 1
    )