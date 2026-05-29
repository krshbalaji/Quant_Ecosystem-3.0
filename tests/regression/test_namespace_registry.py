from quant_ecosystem.cognition.swarm import (
    NamespaceRecord,
    NamespaceRegistry,
)


def test_namespace_registry():

    registry = NamespaceRegistry()

    registry.register(
        NamespaceRecord(
            symbol_name="GovernanceDecision",
            module_name="governance",
        )
    )

    assert registry.count() == 1