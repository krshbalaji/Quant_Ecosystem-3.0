from quant_ecosystem.cognition.swarm import (
    FederationIdentity,
    SovereignCollectiveRouter,
    SwarmMessage,
    TrustRegistry,
)


def test_router_accepts_trusted_messages():

    registry = TrustRegistry()

    registry.register(
        FederationIdentity(
            organism_id="organism-alpha",
            constitutional_hash="CONST-A",
            capabilities={
                "federation_sync": 0.95,
            },
        )
    )

    router = SovereignCollectiveRouter(registry)

    message = SwarmMessage(
        sender_id="organism-alpha",
        message_type="sync",
        payload={
            "state": "stable",
        },
    )

    accepted = router.route(
        message,
        required_capability="federation_sync",
    )

    assert accepted
    assert len(router.message_log) == 1


def test_router_rejects_untrusted_messages():

    registry = TrustRegistry()

    router = SovereignCollectiveRouter(registry)

    message = SwarmMessage(
        sender_id="rogue-node",
        message_type="sync",
        payload={},
    )

    accepted = router.route(
        message,
        required_capability="federation_sync",
    )

    assert not accepted
    assert len(router.message_log) == 0