from quant_ecosystem.cognition.swarm import (
    ExecutionAdapterRegistry,
    FederationExecutionRouterAdapter,
    RouterAdapterContract,
    RouterExecutionRequest,
)


def test_router_adapter():

    registry = ExecutionAdapterRegistry()

    registry.register(
        RouterAdapterContract(
            adapter_id="router-adapter",
            target_router="execution_router",
        )
    )

    adapter = (
        FederationExecutionRouterAdapter(
            registry
        )
    )

    result = adapter.route(
        RouterExecutionRequest(
            request_id="REQ-1",
            route_type="execution",
            payload={},
        ),
        "router-adapter",
    )

    assert result.accepted