from quant_ecosystem.cognition.swarm import (
    FederationArchitectureRegistry,
    FederationTopologyGraph,
    TopologyValidationEngine,
)


def test_topology_validation():

    registry = FederationArchitectureRegistry()
    graph = FederationTopologyGraph()

    engine = TopologyValidationEngine()

    assert engine.validate(
        registry,
        graph,
    )