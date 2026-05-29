from quant_ecosystem.cognition.swarm import (
    CapabilityDependency,
    CapabilityDependencyRegistry,
    FederationDependencyMapper,
)


def test_dependency_mapper():

    registry = (
        CapabilityDependencyRegistry()
    )

    registry.register(
        CapabilityDependency(
            capability_id="audit",
            depends_on="authorization",
        )
    )

    report = (
        FederationDependencyMapper()
        .analyze(registry)
    )

    assert report.dependency_count == 1