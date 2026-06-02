from datetime import datetime, timedelta

from quant_ecosystem.core.multimap_store import MultiMapStore
from quant_ecosystem.cognition.swarm.audit_event import AuditEvent
from quant_ecosystem.cognition.swarm.audit_replay import (
    AuditReplayEngine,
    AuditReplayQuery,
)
from quant_ecosystem.cognition.swarm.topology_audit_result import TopologyAuditResult


def make_event(event_id: str, event_type: str, offset_seconds: int = 0) -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        event_type=event_type,
        source_id="replay-test",
        timestamp=datetime.utcnow() + timedelta(seconds=offset_seconds),
    )


def test_audit_replay_engine_returns_lineage_records_with_pagination():
    store = MultiMapStore()
    key = "audit.execution.lineage.L1"
    store.put(key, make_event("e1", "AUDIT", 0))
    store.put(key, make_event("e2", "AUDIT", 1))
    store.put(key, make_event("e3", "OTHER", 2))

    query = AuditReplayQuery(
        lineage_id="L1",
        event_type="AUDIT",
        limit=1,
        offset=1,
    )

    result = AuditReplayEngine(store).replay(query)

    assert result.source_key == key
    assert result.status == "OK"
    assert result.record_count == 1
    assert len(result.records) == 1
    assert result.records[0].event_id == "e2"
    assert result.first_timestamp == result.last_timestamp
    assert result.issues == []


def test_audit_replay_engine_supports_namespace_and_topology_filters():
    store = MultiMapStore()
    store.put("audit.namespace.alpha", {"namespace": "alpha", "payload": "value"})
    store.put("audit.topology.namespace_registry", TopologyAuditResult(total_symbols=1, duplicate_symbols=0))

    namespace_query = AuditReplayQuery(namespace="alpha")
    namespace_result = AuditReplayEngine(store).replay(namespace_query)

    assert namespace_result.status == "OK"
    assert namespace_result.source_key == "audit.namespace.alpha"
    assert namespace_result.record_count == 1
    assert namespace_result.records[0]["payload"] == "value"

    topology_query = AuditReplayQuery(topology_filter="namespace")
    topology_result = AuditReplayEngine(store).replay(topology_query)

    assert topology_result.status == "OK"
    assert topology_result.source_key == "audit.topology.namespace_registry"
    assert topology_result.record_count == 1
    assert topology_result.records[0].duplicate_symbols == 0


def test_audit_replay_engine_does_not_mutate_multimap_store():
    store = MultiMapStore()
    key = "audit.execution.lineage.PERSIST"
    event = make_event("persist-1", "AUDIT", 0)
    store.put(key, event)

    original_keys = store.keys()
    original_records = store.get(key)

    result = AuditReplayEngine(store).replay(AuditReplayQuery(lineage_id="PERSIST"))

    assert result.status == "OK"
    assert store.keys() == original_keys
    assert store.get(key) == original_records
    assert store.size() == 1


def test_audit_replay_engine_returns_no_records_for_missing_filters():
    store = MultiMapStore()
    result = AuditReplayEngine(store).replay(AuditReplayQuery(namespace="missing"))

    assert result.status == "NO_RECORDS"
    assert "NAMESPACE_NOT_FOUND" in result.issues
    assert result.record_count == 0
