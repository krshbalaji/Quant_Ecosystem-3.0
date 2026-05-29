from quant_ecosystem.cognition.swarm import (
    ExecutionInitiative,
    FederationExecutionGovernanceRegistry,
)


def test_execution_governance_registry():

    registry = (
        FederationExecutionGovernanceRegistry()
    )

    registry.register(
        ExecutionInitiative(
            initiative_id="INIT1",
            description="Improve readiness",
            approved=True,
        )
    )

    assert registry.count() == 1