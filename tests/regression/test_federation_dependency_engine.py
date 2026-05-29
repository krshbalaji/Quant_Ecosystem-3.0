from quant_ecosystem.cognition.swarm import (
    DependencyEdge,
    FederationArchitectureRegistry,
    FederationComponent,
    FederationDependencyEngine,
    FederationTopologyGraph,
)


def test_dependency_analysis():

    registry = (
        FederationArchitectureRegistry()
    )

    registry.register(
        FederationComponent(
            component_id="A",
            component_type="engine",
        )
    )

    graph = FederationTopologyGraph()

    graph.add_edge(
        DependencyEdge(
            source_component="A",
            target_component="B",
        )
    )

    result = (
        FederationDependencyEngine()
        .analyze(
            registry,
            graph,
        )
    )

    assert result.dependency_density > 0