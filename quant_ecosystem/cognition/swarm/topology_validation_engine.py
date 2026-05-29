from .federation_architecture_registry import (
    FederationArchitectureRegistry,
)
from .federation_topology_graph import (
    FederationTopologyGraph,
)


class TopologyValidationEngine:

    def validate(
        self,
        registry: FederationArchitectureRegistry,
        graph: FederationTopologyGraph,
    ) -> bool:

        return (
            registry.count() >= 0
            and graph.edge_count() >= 0
        )