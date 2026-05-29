from quant_ecosystem.cognition.swarm import (
    CapabilityDependency,
    CapabilityDependencyRegistry,
)


def test_dependency_registry():

    registry = (
        CapabilityDependencyRegistry()
    )

    registry.register(
        CapabilityDependency(
            capability_id="governance",
            depends_on="policy",
        )
    )

    assert registry.count() == 1