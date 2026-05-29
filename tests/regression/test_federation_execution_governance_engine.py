from quant_ecosystem.cognition.swarm import (
    ExecutionInitiative,
    FederationExecutionGovernanceEngine,
    FederationExecutionGovernanceRegistry,
)


def test_execution_governance_engine():

    registry = (
        FederationExecutionGovernanceRegistry()
    )

    registry.register(
        ExecutionInitiative(
            initiative_id="INIT1",
            description="Improve governance",
            approved=True,
        )
    )

    decisions = (
        FederationExecutionGovernanceEngine()
        .evaluate(
            registry
        )
    )

    assert len(decisions) == 1
    assert decisions[0].approved