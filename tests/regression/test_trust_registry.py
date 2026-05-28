from quant_ecosystem.cognition.swarm import (
    FederationIdentity,
    TrustRegistry,
)


def test_trust_registry_accepts_known_capability():

    registry = TrustRegistry()

    identity = FederationIdentity(
        organism_id="alpha",
        constitutional_hash="CONST-1",
        capabilities={
            "risk_coordination": 0.9,
        },
    )

    registry.register(identity)

    assert registry.evaluate_trust(
        "alpha",
        "risk_coordination",
    )


def test_trust_registry_rejects_unknown():

    registry = TrustRegistry()

    assert not registry.evaluate_trust(
        "ghost",
        "risk_coordination",
    )