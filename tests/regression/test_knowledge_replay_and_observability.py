from datetime import datetime, timedelta

from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.cognition.swarm import (
    GovernanceObservation,
    GovernanceObservabilityEngine,
    GovernanceObservabilityRegistry,
    KnowledgePattern,
    KnowledgeReplayEngine,
    KnowledgeReplayQuery,
)


def test_knowledge_replay_engine_returns_patterns_with_provenance_and_pagination():
    store = MultiMapStore()
    patterns = [
        KnowledgePattern(
            category="PRICE",
            frequency=5,
            pattern_id="knowledge.PRICE",
            pattern_type="event_type",
            source_keys=("audit.execution.lineage.L-1",),
            first_seen=datetime(2026, 6, 3, 12, 0, 0),
            last_seen=datetime(2026, 6, 3, 12, 5, 0),
            schema_versions=("v1",),
            provenance=("event_type:PRICE",),
        ),
        KnowledgePattern(
            category="SIGNAL",
            frequency=2,
            pattern_id="knowledge.SIGNAL",
            pattern_type="event_type",
            source_keys=("audit.execution.lineage.L-2",),
            first_seen=datetime(2026, 6, 3, 12, 10, 0),
            last_seen=datetime(2026, 6, 3, 12, 15, 0),
            schema_versions=("v2",),
            provenance=("event_type:SIGNAL",),
        ),
    ]

    store.put("audit.learning.pattern.knowledge.PRICE", patterns[0])
    store.put("audit.learning.pattern.knowledge.SIGNAL", patterns[1])

    engine = KnowledgeReplayEngine(store)
    query = KnowledgeReplayQuery(category="PRICE", limit=1, offset=0)
    result = engine.replay(query)

    assert result.status == "OK"
    assert result.record_count == 1
    assert result.records[0].pattern_id == "knowledge.PRICE"
    assert result.source_keys == ["audit.learning.pattern.knowledge.PRICE"]
    assert result.schema_versions == ["v1"]

    query_page = KnowledgeReplayQuery(pattern_type="event_type", limit=1, offset=1)
    page_result = engine.replay(query_page)

    assert page_result.record_count == 1
    assert page_result.records[0].pattern_id == "knowledge.SIGNAL"


def test_knowledge_replay_engine_supports_lineage_and_provenance_lookup():
    store = MultiMapStore()
    pattern = KnowledgePattern(
        category="PRICE",
        frequency=3,
        pattern_id="knowledge.PRICE.TODAY",
        pattern_type="event_type",
        source_keys=("audit.execution.lineage.L-3", "audit.execution.lineage.L-4"),
        provenance=("event_type:PRICE", "event_type:PRICE_ALT"),
    )
    store.put("audit.learning.pattern.knowledge.PRICE.TODAY", pattern)

    engine = KnowledgeReplayEngine(store)
    query = KnowledgeReplayQuery(lineage_id="L-4")
    result = engine.replay(query)

    assert result.record_count == 1
    assert result.records[0].pattern_id == "knowledge.PRICE.TODAY"
    assert result.records[0].provenance == ("event_type:PRICE", "event_type:PRICE_ALT")

    query_prov = KnowledgeReplayQuery(provenance="PRICE_ALT")
    prov_result = engine.replay(query_prov)

    assert prov_result.record_count == 1
    assert prov_result.records[0].pattern_id == "knowledge.PRICE.TODAY"


def test_governance_observability_engine_creates_and_aggregates_observations():
    registry = GovernanceObservabilityRegistry()
    engine = GovernanceObservabilityEngine()

    pattern = KnowledgePattern(
        category="PRICE",
        frequency=4,
        pattern_id="knowledge.PRICE",
        source_keys=("audit.execution.lineage.L-5",),
        aggregated_count=2,
    )

    observation = engine.observe(
        pattern,
        observation_id="obs-1",
        summary="Consolidated price pattern",
        status="REVIEW",
        issues=["MISSING_SCHEMA"],
    )
    engine.register_observation(registry, observation)

    assert registry.count() == 1
    assert registry.get("obs-1") == observation
    assert registry.find_by_pattern("knowledge.PRICE")[0].status == "REVIEW"

    aggregate = engine.aggregate_observations(registry.all())
    assert aggregate.category == "PRICE"
    assert aggregate.metadata["observation_count"] == 1

    traced = engine.trace_origins(pattern)
    assert traced["lineage_ids"] == ["audit.execution.lineage.L-5"]
    assert traced["provenance"] == []

    summary = engine.summarize_evolution(registry.all())
    assert summary["PRICE"]["REVIEW"] == 1
    assert summary["PRICE"]["total"] == 1
