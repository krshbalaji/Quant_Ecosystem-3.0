from quant_ecosystem.cognition.swarm import (
    ArchitectureCategory,
    ArchitectureClassification,
    FederationArchitectureClassificationRegistry,
    FederationArchitectureClassifier,
)


def test_architecture_classifier():

    registry = (
        FederationArchitectureClassificationRegistry()
    )

    registry.register(
        ArchitectureClassification(
            component_name="LifecycleEngine",
            category=(
                ArchitectureCategory.LIFECYCLE
            ),
        )
    )

    report = (
        FederationArchitectureClassifier()
        .evaluate(
            registry
        )
    )

    assert report.total_components == 1
    assert report.total_categories == 1