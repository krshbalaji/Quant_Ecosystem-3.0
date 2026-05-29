from quant_ecosystem.cognition.swarm import (
    FederationTopologyAuditEngine,
    NamespaceRecord,
    NamespaceRegistry,
)


def test_topology_audit_engine():

    registry = NamespaceRegistry()

    registry.register(
        NamespaceRecord(
            symbol_name="GovernanceDecision",
            module_name="governance",
        )
    )

    result = (
        FederationTopologyAuditEngine()
        .evaluate(
            registry
        )
    )

    assert result.total_symbols == 1