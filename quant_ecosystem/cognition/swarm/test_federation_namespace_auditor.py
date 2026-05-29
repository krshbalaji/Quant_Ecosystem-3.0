from quant_ecosystem.cognition.swarm import (
    FederationNamespaceAuditor,
    NamespaceRecord,
    NamespaceRegistry,
)


def test_namespace_audit():

    registry = NamespaceRegistry()

    registry.register(
        NamespaceRecord(
            symbol_name="ExecutionInitiative",
            module_name="module_a",
        )
    )

    registry.register(
        NamespaceRecord(
            symbol_name="ExecutionInitiative",
            module_name="module_b",
        )
    )

    result = (
        FederationNamespaceAuditor()
        .audit(registry)
    )

    assert result.total_symbols == 2
    assert result.duplicate_symbols == 1