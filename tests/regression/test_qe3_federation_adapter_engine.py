from quant_ecosystem.cognition.swarm import (
    GovernanceAdapterContract,
    QE3FederationAdapterEngine,
    QE3FederationAdapterRegistry,
    SubsystemAdapterRequest,
)


def test_adapter_engine():

    registry = (
        QE3FederationAdapterRegistry()
    )

    registry.register(
        GovernanceAdapterContract(
            adapter_id="exec",
            subsystem_name="execution_router",
        )
    )

    engine = (
        QE3FederationAdapterEngine(
            registry
        )
    )

    result = engine.submit(
        SubsystemAdapterRequest(
            request_id="REQ1",
            subsystem_name="execution_router",
            payload={},
        )
    )

    assert result.accepted