from quant_ecosystem.cognition.swarm import (
    FederationWorkflowIntegrator,
    WorkflowContext,
    WorkflowIntegrationRegistry,
    WorkflowStep,
)


def test_integrator_execution():

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
            "policy"
        )
    )

    integrator = (
        FederationWorkflowIntegrator(
            registry
        )
    )

    context = WorkflowContext()

    result = integrator.execute(
        context
    )

    assert result.successful
    assert (
        result.completed_steps
        == 2
    )