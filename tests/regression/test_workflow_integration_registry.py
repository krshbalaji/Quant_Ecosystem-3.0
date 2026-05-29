from quant_ecosystem.cognition.swarm import (
    WorkflowIntegrationRegistry,
    WorkflowStep,
)


def test_registry_tracks_steps():

    registry = (
        WorkflowIntegrationRegistry()
    )

    registry.register(
        WorkflowStep(
            "governance"
        )
    )

    registry.register(
        WorkflowStep(
            "allocation"
        )
    )

    assert (
        len(
            registry.enabled_steps()
        )
        == 2
    )