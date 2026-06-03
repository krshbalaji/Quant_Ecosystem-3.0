from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .knowledge_graph import KnowledgeGraph
from .knowledge_pattern import KnowledgePattern
from .knowledge_registry import KnowledgeRegistry

REASONING_STATUS_OK = "OK"
REASONING_STATUS_NO_RECORDS = "NO_RECORDS"
REASONING_STATUS_INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class ReasoningStep:
    step_index: int
    source_id: str
    target_id: str
    edge_type: str
    transition_kind: str
    edge_metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReasoningChain:
    start_id: str
    end_id: str
    steps: Tuple[ReasoningStep, ...]
    traversed_node_ids: Tuple[str, ...]
    cross_domain: bool
    domain_edge_types: Tuple[str, ...] = field(default_factory=tuple)
    provenance: Tuple[str, ...] = field(default_factory=tuple)


@dataclass
class KnowledgeReasoningResult:
    start_id: str
    chains: List[ReasoningChain]
    traversed_node_ids: Tuple[str, ...]
    provenance: Tuple[str, ...]
    status: str
    issues: List[str] = field(default_factory=list)
    explanation: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    cross_domain_chain_count: int = 0


class CrossDomainReasoningEngine:

    def reason(
        self,
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
        start_id: str,
        max_depth: int = 2,
        relationship_filter: Optional[Sequence[str]] = None,
        dependency_filter: Optional[Sequence[str]] = None,
    ) -> KnowledgeReasoningResult:
        if not start_id:
            return KnowledgeReasoningResult(
                start_id=start_id,
                chains=[],
                traversed_node_ids=(),
                provenance=(),
                status=REASONING_STATUS_INVALID_INPUT,
                issues=["START_ID_REQUIRED"],
                explanation="Start identifier is required for reasoning.",
            )

        start_pattern = graph.get_pattern(start_id) or registry.get(start_id)
        if start_pattern is None:
            return KnowledgeReasoningResult(
                start_id=start_id,
                chains=[],
                traversed_node_ids=(),
                provenance=(),
                status=REASONING_STATUS_NO_RECORDS,
                issues=["START_ID_NOT_FOUND"],
                explanation="No graph node or registry pattern was found for the requested start identifier.",
            )

        traversed_node_ids = tuple(self._deterministic_traverse(graph, start_id, max_depth))
        paths = self._build_reasoning_paths(
            graph,
            registry,
            start_id,
            max_depth,
            relationship_filter,
            dependency_filter,
        )

        chains = [self._build_chain(path, graph, registry) for path in paths]
        provenance = self._collect_provenance(chains, graph, registry)
        cross_domain_count = sum(1 for chain in chains if chain.cross_domain)

        explanation = (
            f"Generated {len(chains)} deterministic reasoning chains from {start_id} "
            f"with {len(traversed_node_ids)} traversed nodes."
        )

        status = REASONING_STATUS_OK if chains else REASONING_STATUS_NO_RECORDS

        return KnowledgeReasoningResult(
            start_id=start_id,
            chains=chains,
            traversed_node_ids=traversed_node_ids,
            provenance=tuple(sorted(provenance)),
            status=status,
            explanation=explanation,
            cross_domain_chain_count=cross_domain_count,
        )

    def _build_reasoning_paths(
        self,
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
        start_id: str,
        max_depth: int,
        relationship_filter: Optional[Sequence[str]],
        dependency_filter: Optional[Sequence[str]],
    ) -> List[List[ReasoningStep]]:
        paths: List[List[ReasoningStep]] = []
        queue: List[Tuple[str, List[ReasoningStep], List[str]]] = [(start_id, [], [start_id])]

        while queue:
            current_id, steps, visited = queue.pop(0)
            depth = len(steps)
            if depth >= max_depth:
                continue

            for step in self._next_steps(
                graph,
                registry,
                current_id,
                relationship_filter,
                dependency_filter,
            ):
                if step.target_id in visited:
                    continue

                new_steps = steps + [step]
                new_visited = visited + [step.target_id]
                paths.append(new_steps)
                queue.append((step.target_id, new_steps, new_visited))

        return paths

    def _next_steps(
        self,
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
        current_id: str,
        relationship_filter: Optional[Sequence[str]],
        dependency_filter: Optional[Sequence[str]],
    ) -> List[ReasoningStep]:
        candidates: List[ReasoningStep] = []
        node_pattern = graph.get_pattern(current_id) or registry.get(current_id)

        for rel in graph.relationships_for(current_id):
            if relationship_filter and rel.relationship_type not in relationship_filter:
                continue
            target_id = rel.target_id if rel.source_id == current_id else rel.source_id
            target_pattern = graph.get_pattern(target_id) or registry.get(target_id)
            categories = self._categories_for(current_id, target_id, graph, registry)
            provenance = self._step_provenance(node_pattern, target_pattern)
            candidates.append(
                ReasoningStep(
                    step_index=0,
                    source_id=current_id,
                    target_id=target_id,
                    edge_type=rel.relationship_type,
                    transition_kind="relationship",
                    edge_metadata={**rel.metadata, "source_category": categories[0], "target_category": categories[1]},
                    provenance=provenance,
                )
            )

        for dep in graph.dependencies_for(current_id):
            if dependency_filter and dep.dependency_type not in dependency_filter:
                continue
            if dep.dependent_id == current_id:
                target_id = dep.dependency_id
            elif dep.dependency_id == current_id:
                target_id = dep.dependent_id
            else:
                continue

            target_pattern = graph.get_pattern(target_id) or registry.get(target_id)
            categories = self._categories_for(current_id, target_id, graph, registry)
            provenance = self._step_provenance(node_pattern, target_pattern)
            candidates.append(
                ReasoningStep(
                    step_index=0,
                    source_id=current_id,
                    target_id=target_id,
                    edge_type=dep.dependency_type,
                    transition_kind="dependency",
                    edge_metadata={**dep.metadata, "source_category": categories[0], "target_category": categories[1]},
                    provenance=provenance,
                )
            )

        return sorted(
            candidates,
            key=lambda step: (
                step.transition_kind,
                step.edge_type,
                step.target_id,
            ),
        )

    def _build_chain(
        self,
        path: List[ReasoningStep],
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
    ) -> ReasoningChain:
        if not path:
            return ReasoningChain(
                start_id="",
                end_id="",
                steps=(),
                traversed_node_ids=(),
                cross_domain=False,
                provenance=(),
            )

        provenance = self._collect_step_provenance(path, graph, registry)
        traversed_node_ids = tuple({step.source_id for step in path} | {path[-1].target_id})
        domain_edge_types = tuple({step.edge_type for step in path if self._is_cross_domain_step(step, graph, registry)})
        cross_domain = any(self._is_cross_domain_step(step, graph, registry) for step in path)

        ordered_steps = tuple(
            ReasoningStep(
                step_index=index,
                **{
                    "source_id": step.source_id,
                    "target_id": step.target_id,
                    "edge_type": step.edge_type,
                    "transition_kind": step.transition_kind,
                    "edge_metadata": step.edge_metadata,
                    "provenance": step.provenance,
                }
            )
            for index, step in enumerate(path)
        )

        return ReasoningChain(
            start_id=path[0].source_id,
            end_id=path[-1].target_id,
            steps=ordered_steps,
            traversed_node_ids=tuple(sorted(traversed_node_ids)),
            cross_domain=cross_domain,
            domain_edge_types=tuple(sorted(domain_edge_types)),
            provenance=tuple(sorted(provenance)),
        )

    def _collect_provenance(
        self,
        chains: Sequence[ReasoningChain],
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
    ) -> List[str]:
        provenance_set = set()
        for chain in chains:
            provenance_set.update(chain.provenance)
            for node_id in chain.traversed_node_ids:
                pattern = graph.get_pattern(node_id) or registry.get(node_id)
                if pattern:
                    provenance_set.update(pattern.provenance)
                    provenance_set.update(pattern.source_keys)
        return sorted(provenance_set)

    def _collect_step_provenance(
        self,
        path: List[ReasoningStep],
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
    ) -> List[str]:
        provenance_set = set()
        for step in path:
            provenance_set.update(step.provenance)
            source = graph.get_pattern(step.source_id) or registry.get(step.source_id)
            target = graph.get_pattern(step.target_id) or registry.get(step.target_id)
            if source:
                provenance_set.update(source.source_keys)
                provenance_set.update(source.provenance)
            if target:
                provenance_set.update(target.source_keys)
                provenance_set.update(target.provenance)
        return sorted(provenance_set)

    def _deterministic_traverse(
        self,
        graph: KnowledgeGraph,
        start_id: str,
        max_depth: int,
    ) -> List[str]:
        visited = [start_id]
        frontier = [start_id]
        depth = 0
        result: List[str] = []

        while frontier and depth < max_depth:
            next_frontier: List[str] = []
            for node_id in sorted(frontier):
                if node_id in result:
                    continue
                result.append(node_id)
                neighbors = self._deterministic_neighbors(graph, node_id)
                for neighbor in neighbors:
                    if neighbor not in visited and neighbor not in next_frontier:
                        next_frontier.append(neighbor)
            visited.extend(next_frontier)
            frontier = next_frontier
            depth += 1

        return result

    def _deterministic_neighbors(self, graph: KnowledgeGraph, node_id: str) -> List[str]:
        neighbors = set()
        for rel in graph.relationships_for(node_id):
            neighbor = rel.target_id if rel.source_id == node_id else rel.source_id
            neighbors.add(neighbor)
        return sorted(neighbors)

    def _categories_for(
        self,
        source_id: str,
        target_id: str,
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
    ) -> Tuple[Optional[str], Optional[str]]:
        source_pattern = graph.get_pattern(source_id) or registry.get(source_id)
        target_pattern = graph.get_pattern(target_id) or registry.get(target_id)
        return (
            source_pattern.category if source_pattern else None,
            target_pattern.category if target_pattern else None,
        )

    def _is_cross_domain_step(
        self,
        step: ReasoningStep,
        graph: KnowledgeGraph,
        registry: KnowledgeRegistry,
    ) -> bool:
        source_category, target_category = self._categories_for(
            step.source_id,
            step.target_id,
            graph,
            registry,
        )
        return bool(source_category and target_category and source_category != target_category)

    def _step_provenance(
        self,
        source_pattern: Optional[KnowledgePattern],
        target_pattern: Optional[KnowledgePattern],
    ) -> Tuple[str, ...]:
        provenance = set()
        if source_pattern:
            provenance.update(source_pattern.provenance)
            provenance.update(source_pattern.source_keys)
        if target_pattern:
            provenance.update(target_pattern.provenance)
            provenance.update(target_pattern.source_keys)
        return tuple(sorted(provenance))
