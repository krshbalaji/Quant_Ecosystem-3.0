from quant_ecosystem.cognition.swarm import (
    FederationArchitectureRegistry,
    FederationComponent,
)


def test_registry_tracks_components():

    registry = FederationArchitectureRegistry()

    registry.register(
        FederationComponent(
            component_id="governance",
            component_type="council",
        )
    )

    assert registry.count() == 1