from quant_ecosystem.cognition.swarm import (
    DependencyEdge,
    FederationTopologyGraph,
)


def test_graph_tracks_edges():

    graph = FederationTopologyGraph()

    graph.add_edge(
        DependencyEdge(
            source_component="governance",
            target_component="allocation",
        )
    )

    assert graph.edge_count() == 1