from quant_ecosystem.cognition.swarm import (
    ArchitectureDecisionReport,
    DecisionActionBridge,
    FederationOrchestrator,
    OrchestrationRegistry,
    OrchestrationStage,
)


def test_decision_action_bridge():

    registry = (
        OrchestrationRegistry()
    )

    registry.register(
        OrchestrationStage(
            stage_name="validate"
        )
    )

    orchestrator = (
        FederationOrchestrator(
            registry
        )
    )

    decision = (
        ArchitectureDecisionReport(
            recommended_category=(
                "governance"
            ),
            priority_score=10.0,
        )
    )

    result = (
        DecisionActionBridge()
        .execute(
            decision,
            orchestrator,
        )
    )

    assert result.successful
    assert result.stages_completed == 1