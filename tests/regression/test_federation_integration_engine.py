from quant_ecosystem.cognition.swarm import (
    FederationAction,
    FederationIntegrationEngine,
    FederationIntegrationRegistry,
    IntegrationContract,
)


def test_integration_handoff():

    registry = FederationIntegrationRegistry()

    registry.register(
        IntegrationContract(
            target_system="execution_router"
        )
    )

    engine = FederationIntegrationEngine(
        registry
    )

    result = engine.handoff(
        FederationAction(
            action_id="A1",
            action_type="allocation",
            payload={},
        ),
        "execution_router",
    )

    assert result.accepted