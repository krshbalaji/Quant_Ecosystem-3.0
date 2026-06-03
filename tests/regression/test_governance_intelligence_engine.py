from datetime import datetime
from unittest.mock import Mock

from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.cognition.swarm import (
    CrossDomainReasoningEngine,
    GovernanceDiagnostic,
    GovernanceInsight,
    GovernanceIntelligenceEngine,
    GovernanceObservabilityEngine,
    GovernanceSummary,
    KnowledgeGraphEngine,
    KnowledgePattern,
    KnowledgeRegistry,
    KnowledgeReplayEngine,
    KnowledgeReplayQuery,
)


def _pattern(
    pattern_id,
    category,
    source_key,
    provenance=(),
    schema_versions=("v1",),
):
    return KnowledgePattern(
        category=category,
        frequency=1,
        pattern_id=pattern_id,
        pattern_type="event_type",
        source_keys=(source_key,),
        first_seen=datetime(2026, 6, 3, 9, 0, 0),
        last_seen=datetime(2026, 6, 3, 9, 5, 0),
        schema_versions=schema_versions,
        provenance=provenance,
    )


def _engine(store):
    return GovernanceIntelligenceEngine(
        reasoning_engine=CrossDomainReasoningEngine(),
        observability_engine=GovernanceObservabilityEngine(),
        replay_engine=KnowledgeReplayEngine(store),
        graph_engine=KnowledgeGraphEngine(),
    )


def _fixture():
    registry = KnowledgeRegistry()
    root = _pattern(
        "knowledge.ROOT",
        "DATA",
        "audit.execution.lineage.L-224-A",
    )
    child = _pattern(
        "knowledge.CHILD",
        "RISK",
        "audit.execution.lineage.L-224-B",
        provenance=("knowledge.ROOT",),
        schema_versions=("v2",),
    )
    registry.register(root)
    registry.register(child)

    store = MultiMapStore()
    store.put("audit.learning.pattern.knowledge.ROOT", root)
    store.put("audit.learning.pattern.knowledge.CHILD", child)
    return registry, store


def test_governance_result_contracts_are_immutable_transient_outputs():
    insight = GovernanceInsight(
        insight_id="reasoning.summary",
        category="reasoning",
        summary="Generated insight",
    )
    diagnostic = GovernanceDiagnostic(
        diagnostic_id="graph.topology",
        status="OK",
        source="KnowledgeGraphEngine",
    )
    summary = GovernanceSummary(
        status="OK",
        selected_pattern_ids=("knowledge.ROOT",),
        insights=(insight,),
        diagnostics=(diagnostic,),
    )

    assert summary.insights[0].category == "reasoning"
    assert summary.diagnostics[0].source == "KnowledgeGraphEngine"
    assert summary.metadata == {}


def test_governance_intelligence_engine_summarizes_reasoning_and_health():
    registry, store = _fixture()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=("knowledge.ROOT",),
        replay_queries=(KnowledgeReplayQuery(pattern_id="knowledge.ROOT"),),
        max_depth=2,
    )

    assert summary.status == "OK"
    assert summary.graph_node_count == 2
    assert summary.relationship_count >= 1
    assert summary.dependency_count >= 1
    assert summary.replay_record_count == 1
    assert "v1" in summary.schema_versions
    assert "audit.execution.lineage.L-224-A" in summary.source_keys
    assert "knowledge.ROOT" in summary.selected_pattern_ids

    reasoning = next(
        insight
        for insight in summary.insights
        if insight.insight_id == "reasoning.summary"
    )
    assert reasoning.metrics["chain_count"] >= 1
    assert reasoning.metrics["cross_domain_chain_count"] >= 1

    health = next(
        insight
        for insight in summary.insights
        if insight.insight_id == "institutional.health"
    )
    assert health.category == "institutional_health"
    assert health.metrics["observation_count"] == 1


def test_governance_intelligence_engine_reports_explainability_fields():
    registry, store = _fixture()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=("knowledge.CHILD",),
        replay_queries=(KnowledgeReplayQuery(pattern_id="knowledge.CHILD"),),
        max_depth=1,
    )

    explainability = next(
        insight
        for insight in summary.insights
        if insight.insight_id == "explainability.provenance"
    )

    assert "knowledge.ROOT" in summary.provenance
    assert "audit.execution.lineage.L-224-B" in explainability.source_keys
    assert explainability.metrics["schema_version_count"] == 1
    assert summary.observation_summary["RISK"]["OK"] == 1


def test_governance_intelligence_engine_reports_missing_pattern_diagnostics():
    registry, store = _fixture()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=("knowledge.UNKNOWN",),
        replay_queries=(KnowledgeReplayQuery(pattern_id="knowledge.UNKNOWN"),),
    )

    assert summary.status == "REVIEW"
    reasoning_diagnostic = next(
        diagnostic
        for diagnostic in summary.diagnostics
        if diagnostic.diagnostic_id == "reasoning.knowledge.UNKNOWN"
    )
    assert reasoning_diagnostic.status == "NO_RECORDS"
    assert "START_ID_NOT_FOUND" in reasoning_diagnostic.issues

    replay_diagnostic = next(
        diagnostic
        for diagnostic in summary.diagnostics
        if diagnostic.source == "KnowledgeReplayEngine"
    )
    assert replay_diagnostic.status == "NO_RECORDS"


def test_governance_intelligence_engine_reports_empty_graph_without_mutation():
    registry = KnowledgeRegistry()
    store = MultiMapStore()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=(),
        replay_queries=(),
    )

    assert summary.status == "REVIEW"
    assert summary.graph_node_count == 0
    assert summary.replay_record_count == 0
    graph_diagnostic = next(
        diagnostic
        for diagnostic in summary.diagnostics
        if diagnostic.diagnostic_id == "graph.topology"
    )
    assert graph_diagnostic.status == "NO_RECORDS"
    assert "GRAPH_EMPTY" in graph_diagnostic.issues
    assert store.keys() == []


def test_governance_intelligence_engine_does_not_register_or_persist():
    registry, store = _fixture()
    observability = Mock(wraps=GovernanceObservabilityEngine())

    engine = GovernanceIntelligenceEngine(
        reasoning_engine=CrossDomainReasoningEngine(),
        observability_engine=observability,
        replay_engine=KnowledgeReplayEngine(store),
        graph_engine=KnowledgeGraphEngine(),
    )

    before_keys = tuple(store.keys())
    before_values = {key: tuple(store.get(key)) for key in before_keys}

    engine.summarize(
        registry,
        pattern_ids=("knowledge.ROOT",),
        replay_queries=(KnowledgeReplayQuery(pattern_id="knowledge.ROOT"),),
    )

    assert tuple(store.keys()) == before_keys
    assert {key: tuple(store.get(key)) for key in before_keys} == before_values
    assert observability.register_observation.call_count == 0
    assert not hasattr(engine, "persist")
    assert not hasattr(engine, "save")
    assert not hasattr(engine, "route")
    assert not hasattr(engine, "execute")


def test_governance_intelligence_engine_declares_no_influence_modes():
    registry, store = _fixture()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=("knowledge.ROOT",),
        replay_queries=(KnowledgeReplayQuery(pattern_id="knowledge.ROOT"),),
    )

    assert summary.metadata["engine_mode"] == "read_only_transient"
    assert summary.metadata["execution_influence"] is False
    assert summary.metadata["routing_influence"] is False
    assert summary.metadata["adaptive_behavior"] is False


def test_governance_intelligence_engine_defaults_to_bounded_pattern_replay():
    registry, store = _fixture()

    summary = _engine(store).summarize(
        registry,
        pattern_ids=("knowledge.ROOT", "knowledge.CHILD"),
        max_depth=1,
    )

    assert summary.replay_record_count == 2
    replay_diagnostics = [
        diagnostic
        for diagnostic in summary.diagnostics
        if diagnostic.source == "KnowledgeReplayEngine"
    ]
    assert len(replay_diagnostics) == 2
    assert all(diagnostic.status == "OK" for diagnostic in replay_diagnostics)
