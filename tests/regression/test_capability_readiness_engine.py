from quant_ecosystem.cognition.swarm import (
    CapabilityDependencyRegistry,
    CapabilityReadinessEngine,
)


def test_readiness():

    registry = (
        CapabilityDependencyRegistry()
    )

    assert (
        CapabilityReadinessEngine()
        .ready(registry)
    )