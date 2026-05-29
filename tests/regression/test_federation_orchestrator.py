from quant_ecosystem.cognition.swarm import (
    FederationOrchestrator,
    OrchestrationRegistry,
    OrchestrationRequest,
    OrchestrationStage,
)


def test_orchestrator_execution():

    registry = OrchestrationRegistry()

    registry.register(
        OrchestrationStage(
            "governance"
        )
    )

    registry.register(
        OrchestrationStage(
            "allocation"
        )
    )

    orchestrator = (
        FederationOrchestrator(
            registry
        )
    )

    result = orchestrator.execute(
        OrchestrationRequest(
            request_id="REQ1",
            workflow_type="capital",
            payload={},
        )
    )

    assert result.successful
    assert result.stages_completed == 2