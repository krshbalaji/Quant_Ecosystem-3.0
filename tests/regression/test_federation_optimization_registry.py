from quant_ecosystem.cognition.swarm import (
    FederationOptimizationRegistry,
    OptimizationCandidate,
)


def test_optimization_registry():

    registry = (
        FederationOptimizationRegistry()
    )

    registry.register(
        OptimizationCandidate(
            category_name="governance",
            component_count=20,
        )
    )

    assert registry.count() == 1