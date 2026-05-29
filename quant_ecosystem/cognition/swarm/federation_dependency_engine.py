from .dependency_analysis_result import (
    DependencyAnalysisResult,
)
from .federation_architecture_registry import (
    FederationArchitectureRegistry,
)
from .federation_topology_graph import (
    FederationTopologyGraph,
)


class FederationDependencyEngine:

    def analyze(
        self,
        registry: FederationArchitectureRegistry,
        graph: FederationTopologyGraph,
    ) -> DependencyAnalysisResult:

        component_count = max(
            registry.count(),
            1,
        )

        density = (
            graph.edge_count()
            / component_count
        )

        isolated = max(
            registry.count()
            - graph.edge_count(),
            0,
        )

        return DependencyAnalysisResult(
            dependency_density=density,
            isolated_components=isolated,
        )