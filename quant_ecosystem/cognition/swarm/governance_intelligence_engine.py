from typing import Iterable, List, Optional, Sequence, Tuple

from .cross_domain_reasoning import (
    CrossDomainReasoningEngine,
    KnowledgeReasoningResult,
)
from .governance_diagnostic import GovernanceDiagnostic
from .governance_insight import GovernanceInsight
from .governance_observation import GovernanceObservation
from .governance_observability_engine import GovernanceObservabilityEngine
from .governance_summary import GovernanceSummary
from .knowledge_graph_engine import KnowledgeGraphEngine
from .knowledge_pattern import KnowledgePattern
from .knowledge_registry import KnowledgeRegistry
from .knowledge_replay import (
    KnowledgeReplayEngine,
    KnowledgeReplayQuery,
    KnowledgeReplayResult,
)


class GovernanceIntelligenceEngine:

    def __init__(
        self,
        reasoning_engine: CrossDomainReasoningEngine,
        observability_engine: GovernanceObservabilityEngine,
        replay_engine: KnowledgeReplayEngine,
        graph_engine: KnowledgeGraphEngine,
    ) -> None:
        self._reasoning_engine = reasoning_engine
        self._observability_engine = observability_engine
        self._replay_engine = replay_engine
        self._graph_engine = graph_engine

    def summarize(
        self,
        knowledge_registry: KnowledgeRegistry,
        pattern_ids: Optional[Sequence[str]] = None,
        replay_queries: Optional[Sequence[KnowledgeReplayQuery]] = None,
        max_depth: int = 2,
    ) -> GovernanceSummary:
        graph = self._graph_engine.build_graph(knowledge_registry)
        selected_pattern_ids = self._select_pattern_ids(knowledge_registry, pattern_ids)

        diagnostics: List[GovernanceDiagnostic] = [
            GovernanceDiagnostic(
                diagnostic_id="graph.topology",
                status="OK" if graph.nodes else "NO_RECORDS",
                source="KnowledgeGraphEngine",
                issues=() if graph.nodes else ("GRAPH_EMPTY",),
                details={
                    "node_count": len(graph.nodes),
                    "relationship_count": len(graph.relationships),
                    "dependency_count": len(graph.dependencies),
                },
            )
        ]

        reasoning_results: List[KnowledgeReasoningResult] = []
        for pattern_id in selected_pattern_ids:
            result = self._reasoning_engine.reason(
                graph,
                knowledge_registry,
                pattern_id,
                max_depth=max_depth,
            )
            reasoning_results.append(result)
            diagnostics.append(self._diagnostic_from_reasoning(result))

        replay_results = self._run_replay_queries(
            selected_pattern_ids,
            replay_queries,
        )
        diagnostics.extend(self._diagnostic_from_replay(result) for result in replay_results)

        observations = self._build_observations(
            knowledge_registry,
            reasoning_results,
        )
        observation_summary = self._observability_engine.summarize_evolution(observations)

        insights = tuple(
            self._build_insights(
                knowledge_registry,
                reasoning_results,
                replay_results,
                observations,
            )
        )

        status = "OK"
        if any(diagnostic.status not in ("OK",) for diagnostic in diagnostics):
            status = "REVIEW"

        return GovernanceSummary(
            status=status,
            selected_pattern_ids=selected_pattern_ids,
            insights=insights,
            diagnostics=tuple(diagnostics),
            observation_summary=observation_summary,
            schema_versions=self._schema_versions(replay_results),
            provenance=self._provenance(knowledge_registry, reasoning_results, replay_results),
            source_keys=self._source_keys(knowledge_registry, replay_results),
            graph_node_count=len(graph.nodes),
            relationship_count=len(graph.relationships),
            dependency_count=len(graph.dependencies),
            replay_record_count=sum(result.record_count for result in replay_results),
            metadata={
                "engine_mode": "read_only_transient",
                "execution_influence": False,
                "routing_influence": False,
                "adaptive_behavior": False,
            },
        )

    def _select_pattern_ids(
        self,
        knowledge_registry: KnowledgeRegistry,
        pattern_ids: Optional[Sequence[str]],
    ) -> Tuple[str, ...]:
        if pattern_ids is not None:
            return tuple(pattern_ids)
        return tuple(
            sorted(
                pattern.pattern_id
                for pattern in knowledge_registry.all()
                if pattern.pattern_id
            )
        )

    def _run_replay_queries(
        self,
        pattern_ids: Sequence[str],
        replay_queries: Optional[Sequence[KnowledgeReplayQuery]],
    ) -> List[KnowledgeReplayResult]:
        queries = list(replay_queries or [])
        if not queries:
            queries = [
                KnowledgeReplayQuery(pattern_id=pattern_id, limit=25)
                for pattern_id in pattern_ids
            ]
        return [self._replay_engine.replay(query) for query in queries]

    def _build_observations(
        self,
        knowledge_registry: KnowledgeRegistry,
        reasoning_results: Sequence[KnowledgeReasoningResult],
    ) -> List[GovernanceObservation]:
        observations: List[GovernanceObservation] = []
        for result in reasoning_results:
            pattern = knowledge_registry.get(result.start_id)
            if pattern is None:
                continue
            observations.append(
                self._observability_engine.observe(
                    pattern,
                    observation_id=f"governance.intelligence.{result.start_id}",
                    summary=result.explanation,
                    status=result.status,
                    issues=result.issues,
                    metadata={
                        "chain_count": len(result.chains),
                        "cross_domain_chain_count": result.cross_domain_chain_count,
                        "traversed_node_count": len(result.traversed_node_ids),
                    },
                )
            )
        return observations

    def _build_insights(
        self,
        knowledge_registry: KnowledgeRegistry,
        reasoning_results: Sequence[KnowledgeReasoningResult],
        replay_results: Sequence[KnowledgeReplayResult],
        observations: Sequence[GovernanceObservation],
    ) -> Iterable[GovernanceInsight]:
        total_chains = sum(len(result.chains) for result in reasoning_results)
        cross_domain_chains = sum(result.cross_domain_chain_count for result in reasoning_results)
        traversed_nodes = sorted(
            {
                node_id
                for result in reasoning_results
                for node_id in result.traversed_node_ids
            }
        )

        yield GovernanceInsight(
            insight_id="reasoning.summary",
            category="reasoning",
            summary=(
                f"Generated {total_chains} reasoning chains with "
                f"{cross_domain_chains} cross-domain chains."
            ),
            severity="INFO" if total_chains else "REVIEW",
            source_pattern_ids=tuple(result.start_id for result in reasoning_results),
            provenance=self._reasoning_provenance(reasoning_results),
            explanation="Deterministic chain counts from CrossDomainReasoningEngine.",
            metrics={
                "chain_count": total_chains,
                "cross_domain_chain_count": cross_domain_chains,
                "traversed_node_count": len(traversed_nodes),
            },
        )

        replay_issues = tuple(
            sorted({issue for result in replay_results for issue in result.issues})
        )
        yield GovernanceInsight(
            insight_id="diagnostics.replay",
            category="governance_diagnostics",
            summary=(
                f"Replay returned {sum(result.record_count for result in replay_results)} "
                f"records across {len(replay_results)} queries."
            ),
            severity="REVIEW" if replay_issues else "INFO",
            source_keys=tuple(
                sorted({key for result in replay_results for key in result.source_keys})
            ),
            provenance=self._replay_provenance(replay_results),
            explanation="Read-only replay diagnostics from KnowledgeReplayEngine.",
            metrics={
                "query_count": len(replay_results),
                "record_count": sum(result.record_count for result in replay_results),
                "issue_count": len(replay_issues),
            },
        )

        patterns = [
            pattern
            for pattern in knowledge_registry.all()
            if pattern.pattern_id
        ]
        yield GovernanceInsight(
            insight_id="explainability.provenance",
            category="explainability",
            summary=(
                f"Collected {len(self._source_keys(knowledge_registry, replay_results))} "
                f"source keys and {len(self._provenance(knowledge_registry, reasoning_results, replay_results))} "
                f"provenance references."
            ),
            severity="INFO",
            source_pattern_ids=tuple(sorted(pattern.pattern_id for pattern in patterns if pattern.pattern_id)),
            source_keys=self._source_keys(knowledge_registry, replay_results),
            provenance=self._provenance(knowledge_registry, reasoning_results, replay_results),
            explanation="Explainability report combines source keys, provenance, and replay schema versions.",
            metrics={
                "schema_version_count": len(self._schema_versions(replay_results)),
                "pattern_count": len(patterns),
            },
        )

        observation_categories = sorted({obs.category for obs in observations if obs.category})
        health_severity = "INFO"
        if replay_issues or any(result.status != "OK" for result in reasoning_results):
            health_severity = "REVIEW"
        yield GovernanceInsight(
            insight_id="institutional.health",
            category="institutional_health",
            summary=(
                f"Observed {len(observations)} governance observations across "
                f"{len(observation_categories)} categories."
            ),
            severity=health_severity,
            source_pattern_ids=tuple(obs.pattern_id for obs in observations if obs.pattern_id),
            source_keys=tuple(sorted({key for obs in observations for key in obs.source_keys})),
            provenance=self._reasoning_provenance(reasoning_results),
            explanation="Institutional health reflects transient observation coverage and reasoning diagnostics.",
            metrics={
                "observation_count": len(observations),
                "category_count": len(observation_categories),
                "diagnostic_issue_count": len(replay_issues)
                + sum(len(result.issues) for result in reasoning_results),
            },
        )

    def _diagnostic_from_reasoning(
        self,
        result: KnowledgeReasoningResult,
    ) -> GovernanceDiagnostic:
        return GovernanceDiagnostic(
            diagnostic_id=f"reasoning.{result.start_id}",
            status=result.status,
            source="CrossDomainReasoningEngine",
            issues=tuple(result.issues),
            details={
                "chain_count": len(result.chains),
                "cross_domain_chain_count": result.cross_domain_chain_count,
                "traversed_node_count": len(result.traversed_node_ids),
                "explanation": result.explanation,
            },
        )

    def _diagnostic_from_replay(
        self,
        result: KnowledgeReplayResult,
    ) -> GovernanceDiagnostic:
        return GovernanceDiagnostic(
            diagnostic_id="replay.knowledge",
            status=result.status,
            source="KnowledgeReplayEngine",
            issues=tuple(result.issues),
            details={
                "record_count": result.record_count,
                "source_keys": tuple(result.source_keys),
                "schema_versions": tuple(result.schema_versions),
            },
        )

    def _schema_versions(
        self,
        replay_results: Sequence[KnowledgeReplayResult],
    ) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    version
                    for result in replay_results
                    for version in result.schema_versions
                }
            )
        )

    def _source_keys(
        self,
        knowledge_registry: KnowledgeRegistry,
        replay_results: Sequence[KnowledgeReplayResult],
    ) -> Tuple[str, ...]:
        keys = {
            key
            for pattern in knowledge_registry.all()
            for key in pattern.source_keys
        }
        keys.update(key for result in replay_results for key in result.source_keys)
        return tuple(sorted(keys))

    def _provenance(
        self,
        knowledge_registry: KnowledgeRegistry,
        reasoning_results: Sequence[KnowledgeReasoningResult],
        replay_results: Sequence[KnowledgeReplayResult],
    ) -> Tuple[str, ...]:
        provenance = {
            item
            for pattern in knowledge_registry.all()
            for item in pattern.provenance
        }
        provenance.update(self._reasoning_provenance(reasoning_results))
        provenance.update(self._replay_provenance(replay_results))
        return tuple(sorted(provenance))

    def _reasoning_provenance(
        self,
        reasoning_results: Sequence[KnowledgeReasoningResult],
    ) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item
                    for result in reasoning_results
                    for item in result.provenance
                }
            )
        )

    def _replay_provenance(
        self,
        replay_results: Sequence[KnowledgeReplayResult],
    ) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item
                    for result in replay_results
                    for record in result.records
                    for item in record.provenance
                }
            )
        )
