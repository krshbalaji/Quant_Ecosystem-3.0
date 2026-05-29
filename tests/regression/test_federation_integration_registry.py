from quant_ecosystem.cognition.swarm import (
    FederationIntegrationRegistry,
    IntegrationContract,
)


def test_registry_tracks_contracts():

    registry = FederationIntegrationRegistry()

    registry.register(
        IntegrationContract(
            target_system="execution_router"
        )
    )

    assert registry.enabled(
        "execution_router"
    )