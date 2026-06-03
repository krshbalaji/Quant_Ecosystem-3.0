from datetime import datetime

from quant_ecosystem.cognition.swarm import (
    AuditReplayQuery,
    AuditReplayResult,
    AuditEvent,
    CollectiveLearningEngine,
    LearningPatternRegistry,
)


def test_collective_learning_engine_extracts_learning_patterns_from_audit_replay_result():

    records = [
        AuditEvent(
            event_id="e1",
            event_type="PRICE",
            source_id="source",
            timestamp=datetime.utcnow(),
        ),
        AuditEvent(
            event_id="e2",
            event_type="PRICE",
            source_id="source",
            timestamp=datetime.utcnow(),
        ),
        AuditEvent(
            event_id="e1",
            event_type="PRICE",
            source_id="source",
            timestamp=datetime.utcnow(),
        ),
        {
            "event_type": "SIGNAL",
            "event_id": "s1",
            "timestamp": datetime.utcnow(),
        },
    ]

    result = AuditReplayResult(
        query=AuditReplayQuery(lineage_id="L-1"),
        source_key="audit.execution.lineage.L-1",
        record_count=4,
        first_timestamp=datetime.utcnow(),
        last_timestamp=datetime.utcnow(),
        schema_versions=[],
        status="OK",
        issues=[],
        records=records,
    )

    engine = CollectiveLearningEngine()
    before_records = list(result.records)

    patterns = engine.extract_patterns(result)

    assert result.records == before_records
    assert len(patterns) == 2

    price_pattern = next(
        pattern for pattern in patterns if pattern.classification_key == "PRICE"
    )

    assert price_pattern.frequency == 3
    assert price_pattern.repeated_event_count == 1
    assert price_pattern.anomaly_count == 0
    assert price_pattern.source_key == "audit.execution.lineage.L-1"

    signal_pattern = next(
        pattern for pattern in patterns if pattern.classification_key == "SIGNAL"
    )

    assert signal_pattern.frequency == 1
    assert signal_pattern.repeated_event_count == 0
    assert signal_pattern.anomaly_count == 0


def test_learning_pattern_registry_registers_and_finds_patterns():

    registry = LearningPatternRegistry()
    engine = CollectiveLearningEngine()

    result = AuditReplayResult(
        query=AuditReplayQuery(lineage_id="L-2"),
        source_key="audit.execution.lineage.L-2",
        record_count=1,
        first_timestamp=datetime.utcnow(),
        last_timestamp=datetime.utcnow(),
        schema_versions=[],
        status="OK",
        issues=[],
        records=[
            {
                "event_type": "ANOMALY",
                "event_id": "x1",
            }
        ],
    )

    patterns = engine.extract_patterns(result)
    engine.register_patterns(registry, patterns)

    assert registry.count() == 1
    assert registry.get("event_type:ANOMALY") is not None
    assert registry.find_by_type("event_type")[0].classification_key == "ANOMALY"
    assert registry.keys() == ["event_type:ANOMALY"]
