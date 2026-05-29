from quant_ecosystem.cognition.swarm import (
    FederationNamespaceAuditor,
    NamespaceRecord,
    NamespaceRegistry,
)


def test_namespace_audit():

    registry = NamespaceRegistry()

    registry.register(
        NamespaceRecord(
            symbol_name="A",
            module_name="mod1",
        )
    )

    registry.register(
        NamespaceRecord(
            symbol_name="A",
            module_name="mod2",
        )
    )

    result = (
        FederationNamespaceAuditor()
        .audit(registry)
    )

    assert result.duplicate_symbols == 1