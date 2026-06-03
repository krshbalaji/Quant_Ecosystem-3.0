from typing import Dict, List, Optional, Sequence

from .knowledge_dependency import KnowledgeDependency
from .knowledge_pattern import KnowledgePattern
from .knowledge_relationship import KnowledgeRelationship


class KnowledgeGraph:

    def __init__(self) -> None:
        self.nodes: Dict[str, KnowledgePattern] = {}
        self.relationships: List[KnowledgeRelationship] = []
        self.dependencies: List[KnowledgeDependency] = []

    def add_pattern(
        self,
        pattern: KnowledgePattern,
    ) -> None:
        if pattern.pattern_id:
            self.nodes[pattern.pattern_id] = pattern

    def add_relationship(
        self,
        relationship: KnowledgeRelationship,
    ) -> None:
        self.relationships.append(relationship)

    def add_dependency(
        self,
        dependency: KnowledgeDependency,
    ) -> None:
        self.dependencies.append(dependency)

    def get_pattern(
        self,
        pattern_id: str,
    ) -> Optional[KnowledgePattern]:
        return self.nodes.get(pattern_id)

    def pattern_ids(self) -> List[str]:
        return list(self.nodes.keys())

    def relationships_for(
        self,
        pattern_id: str,
    ) -> List[KnowledgeRelationship]:
        return [
            rel
            for rel in self.relationships
            if rel.source_id == pattern_id or rel.target_id == pattern_id
        ]

    def dependencies_for(
        self,
        pattern_id: str,
    ) -> List[KnowledgeDependency]:
        return [
            dep
            for dep in self.dependencies
            if dep.dependent_id == pattern_id or dep.dependency_id == pattern_id
        ]

    def traverse(
        self,
        start_id: str,
        max_depth: int = 1,
    ) -> List[str]:
        visited = set()
        frontier = [start_id]
        depth = 0
        result: List[str] = []

        while frontier and depth < max_depth:
            next_frontier: List[str] = []
            for node_id in frontier:
                if node_id in visited:
                    continue
                visited.add(node_id)
                result.append(node_id)
                neighbors = {
                    rel.target_id
                    for rel in self.relationships
                    if rel.source_id == node_id
                } | {
                    rel.source_id
                    for rel in self.relationships
                    if rel.target_id == node_id
                }
                for neighbor in neighbors:
                    if neighbor not in visited:
                        next_frontier.append(neighbor)
            frontier = next_frontier
            depth += 1

        return result
