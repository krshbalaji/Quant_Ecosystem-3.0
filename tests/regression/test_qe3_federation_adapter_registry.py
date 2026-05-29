from quant_ecosystem.cognition.swarm import (
    GovernanceAdapterContract,
    QE3FederationAdapterRegistry,
)


def test_registry():

    registry = (
        QE3FederationAdapterRegistry()
    )

    registry.register(
        GovernanceAdapterContract(
            adapter_id="risk",
            subsystem_name="risk_engine",
        )
    )

    assert registry.enabled(
        "risk_engine"
    )