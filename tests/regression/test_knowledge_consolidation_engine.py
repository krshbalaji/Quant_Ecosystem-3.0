from datetime import datetime

from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.cognition.swarm import (
    KnowledgeConsolidationEngine,
    KnowledgeRegistry,
    KnowledgePattern,
    LearningPattern,
)


def test_knowledge_consolidation_engine_consolidates_learning_patterns():

    learned_patterns = [
        LearningPattern(
            pattern_id="event_type:PRICE",
            pattern_type="event_type",
            classification_key="PRICE",
            frequency=3,
            anomaly_count=1,
            repeated_event_count=1,
            source_key="audit.execution.lineage.L-1",
            first_seen=datetime(2026, 6, 3, 12, 0, 0),
            last_seen=datetime(2026, 6, 3, 12, 5, 0),
            schema_versions=("v1",),
        ),
        LearningPattern(
            pattern_id="event_type:PRICE_ALT",
            pattern_type="event_type",
            classification_key="PRICE",
            frequency=2,
            anomaly_count=0,
            repeated_event_count=0,
            source_key="audit.execution.lineage.L-2",
            first_seen=datetime(2026, 6, 3, 12, 10, 0),
            last_seen=datetime(2026, 6, 3, 12, 15, 0),
            schema_versions=("v1",),
        ),
        LearningPattern(
            pattern_id="event_type:SIGNAL",
            pattern_type="event_type",
            classification_key="SIGNAL",
            frequency=1,
            anomaly_count=0,
            repeated_event_count=0,
            source_key="audit.execution.lineage.L-3",
            first_seen=datetime(2026, 6, 3, 12, 20, 0),
            last_seen=datetime(2026, 6, 3, 12, 20, 0),
            schema_versions=("v2",),
        ),
    ]

    engine = KnowledgeConsolidationEngine()
    consolidated = engine.consolidate(learned_patterns)

    assert len(consolidated) == 2

    price_knowledge = next(
        pattern for pattern in consolidated if pattern.category == "PRICE"
    )
    signal_knowledge = next(
        pattern for pattern in consolidated if pattern.category == "SIGNAL"
    )

    assert price_knowledge.frequency == 5
    assert price_knowledge.aggregated_count == 2
    assert price_knowledge.source_keys == (
        "audit.execution.lineage.L-1",
        "audit.execution.lineage.L-2",
    )
    assert price_knowledge.provenance == (
        "event_type:PRICE",
        "event_type:PRICE_ALT",
    )
    assert price_knowledge.metadata["anomaly_count"] == 1
    assert price_knowledge.metadata["repeated_event_count"] == 1
    assert price_knowledge.schema_versions == ("v1",)

    assert signal_knowledge.frequency == 1
    assert signal_knowledge.aggregated_count == 1
    assert signal_knowledge.pattern_type == "event_type"


def test_knowledge_consolidation_engine_persists_patterns_to_multimap_store():

    patterns = [
        KnowledgePattern(
            category="PRICE",
            frequency=5,
            pattern_id="knowledge.PRICE",
        )
    ]

    store = MultiMapStore()
    engine = KnowledgeConsolidationEngine()
    engine.persist(store, patterns)

    stored = store.get("audit.learning.pattern.knowledge.PRICE")
    assert len(stored) == 1
    assert stored[0].category == "PRICE"
    assert stored[0].frequency == 5


def test_knowledge_registry_registers_and_retrieves_patterns():

    registry = KnowledgeRegistry()
    knowledge = KnowledgePattern(
        category="SIGNAL",
        frequency=1,
        pattern_id="knowledge.SIGNAL",
    )

    registry.register(knowledge)

    assert registry.count() == 1
    assert registry.get("knowledge.SIGNAL") == knowledge
    assert registry.find_by_category("SIGNAL") == [knowledge]
    assert registry.keys() == ["knowledge.SIGNAL"]
