from quant_ecosystem.cognition.swarm import (
    FederationArchitectureRegistry,
    FederationTopologyAnalyzer,
    FederationTopologyGraph,
)


def test_topology_health():

    result = (
        FederationTopologyAnalyzer()
        .evaluate(
            FederationArchitectureRegistry(),
            FederationTopologyGraph(),
        )
    )

    assert result.healthy