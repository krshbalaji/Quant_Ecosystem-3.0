from quant_ecosystem.cognition.swarm import (
    FederationHealthCheck,
)


def test_health_check():

    health = (
        FederationHealthCheck(
            healthy=True,
            component_count=1,
        )
    )

    assert health.healthy