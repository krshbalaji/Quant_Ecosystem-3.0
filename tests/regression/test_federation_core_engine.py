from quant_ecosystem.cognition.swarm import (
    FederationCoreEngine,
    FederationRegistry,
)


def test_core_engine():

    registry = FederationRegistry()

    result = (
        FederationCoreEngine()
        .evaluate(
            registry
        )
    )

    assert result.healthy