from quant_ecosystem.cognition.swarm import (
    FederationRoadmapEngine,
    FederationRoadmapRegistry,
    PrioritizedObjective,
)


def test_roadmap_generation():

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

    roadmap = (
        FederationRoadmapEngine()
        .generate(
            registry
        )
    )

    assert (
        roadmap.roadmap_steps[0]
        .execution_order
        == 1
    )