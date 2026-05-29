from quant_ecosystem.cognition.swarm import (
    OrchestrationRegistry,
    OrchestrationStage,
)


def test_registry_counts_stages():

    registry = OrchestrationRegistry()

    registry.register(
        OrchestrationStage(
            "governance"
        )
    )

    registry.register(
        OrchestrationStage(
            "authorization"
        )
    )

    assert registry.enabled_count() == 2