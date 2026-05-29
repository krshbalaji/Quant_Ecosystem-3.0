from typing import List

from .dependency_edge import DependencyEdge


class FederationTopologyGraph:

    def __init__(self):
        self.edges: List[DependencyEdge] = []

    def add_edge(
        self,
        edge: DependencyEdge,
    ) -> None:

        self.edges.append(edge)

    def edge_count(self) -> int:

        return len(self.edges)