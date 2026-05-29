from quant_ecosystem.cognition.swarm import (
    FederationEntity,
    FederationRegistry,
)


def test_registry_tracks_entities():

    registry = FederationRegistry()

    registry.register(
        FederationEntity(
            entity_id="A",
            entity_type="engine",
        )
    )

    assert registry.count() == 1