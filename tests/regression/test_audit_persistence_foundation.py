from datetime import datetime

from quant_ecosystem.cognition.swarm import (
    ExecutionLineage,
    FederationAuditRegistry,
    FederationNamespaceAuditor,
    NamespaceRecord,
    NamespaceRegistry,
)
from quant_ecosystem.cognition.swarm.audit_event import AuditEvent


def make_event(i: int) -> AuditEvent:
    return AuditEvent(
        event_id=f"event-{i}",
        event_type="AUDIT_TEST",
        source_id="source",
        timestamp=datetime.utcnow(),
    )


def test_federation_audit_registry_shadow_persists_lineage_id():
    registry = FederationAuditRegistry()
    lineage = ExecutionLineage(lineage_id="REG1")

    registry.register(lineage)

    assert registry.exists("REG1")
    assert registry._shadow_store.get("audit.execution.lineage_registry") == ["REG1"]


def test_federation_namespace_auditor_shadow_persists_topology_audit_result():
    registry = NamespaceRegistry()
    registry.register(
        NamespaceRecord(
            symbol_name="X",
            module_name="module_a",
        )
    )
    registry.register(
        NamespaceRecord(
            symbol_name="X",
            module_name="module_b",
        )
    )

    auditor = FederationNamespaceAuditor()
    result = auditor.audit(registry)

    assert result.duplicate_symbols == 1
    stored = auditor._shadow_store.get("audit.topology.namespace_registry")
    assert stored == [result]
