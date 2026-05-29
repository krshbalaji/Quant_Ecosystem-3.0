from .dependency_health_report import (
    DependencyHealthReport,
)
from .federation_dependency_engine import (
    FederationDependencyEngine,
)
from .federation_architecture_registry import (
    FederationArchitectureRegistry,
)
from .federation_topology_graph import (
    FederationTopologyGraph,
)


class FederationTopologyAnalyzer:

    def __init__(self):
        self.engine = (
            FederationDependencyEngine()
        )

    def evaluate(
        self,
        registry: FederationArchitectureRegistry,
        graph: FederationTopologyGraph,
    ) -> DependencyHealthReport:

        result = self.engine.analyze(
            registry,
            graph,
        )

        return DependencyHealthReport(
            healthy=(
                result.dependency_density
                >= 0.0
            ),
            dependency_density=(
                result.dependency_density
            ),
        )