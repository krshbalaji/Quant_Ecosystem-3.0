from quant_ecosystem.cognition.swarm import (
    ExecutionAdapterRegistry,
    RouterAdapterContract,
)


def test_registry_tracks_adapter():

    registry = ExecutionAdapterRegistry()

    registry.register(
        RouterAdapterContract(
            adapter_id="router-adapter",
            target_router="execution_router",
        )
    )

    assert registry.enabled(
        "router-adapter"
    )