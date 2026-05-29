from quant_ecosystem.cognition.swarm import (
    WorkflowDefinition,
    WorkflowRegistry,
)


def test_workflow_registry():

    registry = WorkflowRegistry()

    registry.register(
        WorkflowDefinition(
            workflow_id="WF1",
            stages=["governance"],
        )
    )

    assert (
        registry.get("WF1")
        is not None
    )