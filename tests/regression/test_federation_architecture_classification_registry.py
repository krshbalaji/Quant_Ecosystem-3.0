from quant_ecosystem.cognition.swarm import (
    ArchitectureCategory,
    ArchitectureClassification,
    FederationArchitectureClassificationRegistry,
)


def test_classification_registry():

    registry = (
        FederationArchitectureClassificationRegistry()
    )

    registry.register(
        ArchitectureClassification(
            component_name="GovernanceEngine",
            category=(
                ArchitectureCategory.GOVERNANCE
            ),
        )
    )

    assert registry.count() == 1