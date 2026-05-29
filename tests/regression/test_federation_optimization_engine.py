from quant_ecosystem.cognition.swarm import (
    FederationOptimizationEngine,
    FederationOptimizationRegistry,
    OptimizationCandidate,
)


def test_optimization_engine():

    registry = (
        FederationOptimizationRegistry()
    )

    registry.register(
        OptimizationCandidate(
            category_name="governance",
            component_count=20,
        )
    )

    registry.register(
        OptimizationCandidate(
            category_name="topology",
            component_count=10,
        )
    )

    report = (
        FederationOptimizationEngine()
        .evaluate(
            registry
        )
    )

    assert report.target_category == "governance"