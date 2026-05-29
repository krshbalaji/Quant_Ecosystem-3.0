from quant_ecosystem.cognition.swarm import (
    DiplomaticPosition,
    FederationConflictResolver,
)


def test_conflict_resolver_returns_resolution():

    resolver = FederationConflictResolver()

    left = DiplomaticPosition(
        organism_id="alpha",
        objectives={
            "risk": 0.9,
        },
    )

    right = DiplomaticPosition(
        organism_id="beta",
        objectives={
            "risk": 0.85,
        },
    )

    result = resolver.resolve(
        left,
        right,
        "risk",
    )

    assert result["resolution"] == "cooperate"