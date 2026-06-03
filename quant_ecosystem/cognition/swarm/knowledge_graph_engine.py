from collections import deque, defaultdict
from typing import Dict, List, Optional, Sequence

from .knowledge_dependency import KnowledgeDependency
from .knowledge_graph import KnowledgeGraph
from .knowledge_pattern import KnowledgePattern
from .knowledge_relationship import KnowledgeRelationship
from .knowledge_registry import KnowledgeRegistry


class KnowledgeGraphEngine:

    def build_graph(
        self,
        registry: KnowledgeRegistry,
    ) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        patterns = {pattern.pattern_id: pattern for pattern in registry.all() if pattern.pattern_id}

        for pattern in patterns.values():
            graph.add_pattern(pattern)

        for pattern in patterns.values():
            self._link_provenance(pattern, patterns, graph)
            self._link_dependencies(pattern, graph)

        return graph

    def discover_relationships(
        self,
        graph: KnowledgeGraph,
        relationship_type: Optional[str] = None,
    ) -> List[KnowledgeRelationship]:
        if relationship_type is None:
            return list(graph.relationships)
        return [
            rel
            for rel in graph.relationships
            if rel.relationship_type == relationship_type
        ]

    def map_dependencies(
        self,
        graph: KnowledgeGraph,
        dependency_type: Optional[str] = None,
    ) -> List[KnowledgeDependency]:
        if dependency_type is None:
            return list(graph.dependencies)
        return [
            dep
            for dep in graph.dependencies
            if dep.dependency_type == dependency_type
        ]

    def generate_lineage_graph(
        self,
        graph: KnowledgeGraph,
        pattern_id: str,
    ) -> KnowledgeGraph:
        lineage_graph = KnowledgeGraph()
        visited = set()
        queue = deque([pattern_id])

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            pattern = graph.get_pattern(current)
            if pattern:
                lineage_graph.add_pattern(pattern)
            for rel in graph.relationships_for(current):
                lineage_graph.add_relationship(rel)
                if rel.source_id not in visited:
                    queue.append(rel.source_id)
                if rel.target_id not in visited:
                    queue.append(rel.target_id)
            for dep in graph.dependencies_for(current):
                lineage_graph.add_dependency(dep)
                if dep.dependent_id not in visited:
                    queue.append(dep.dependent_id)
                if dep.dependency_id not in visited:
                    queue.append(dep.dependency_id)

        return lineage_graph

    def traverse(
        self,
        graph: KnowledgeGraph,
        start_id: str,
        max_depth: int = 2,
    ) -> List[str]:
        return graph.traverse(start_id, max_depth=max_depth)

    def _link_provenance(
        self,
        pattern: KnowledgePattern,
        patterns: Dict[str, KnowledgePattern],
        graph: KnowledgeGraph,
    ) -> None:
        for provenance_id in pattern.provenance:
            target = patterns.get(provenance_id)
            relationship = KnowledgeRelationship(
                source_id=pattern.pattern_id,
                target_id=provenance_id,
                relationship_type="derived_from",
                metadata={
                    "target_exists": target is not None,
                },
            )
            graph.add_relationship(relationship)

    def _link_dependencies(
        self,
        pattern: KnowledgePattern,
        graph: KnowledgeGraph,
    ) -> None:
        for source_key in pattern.source_keys:
            dependency = KnowledgeDependency(
                dependent_id=pattern.pattern_id or pattern.category,
                dependency_id=source_key,
                dependency_type="audit_lineage",
                metadata={
                    "source_key": source_key,
                },
            )
            graph.add_dependency(dependency)
