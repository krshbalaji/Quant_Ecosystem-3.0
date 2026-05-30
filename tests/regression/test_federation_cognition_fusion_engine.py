from quant_ecosystem.cognition.swarm import (
    FederationCognitionSnapshot,
    FederationCognitionFusionEngine,
)


def test_fusion_engine():

    snapshot = FederationCognitionSnapshot(
        performance=1.0,
        risk=0.5,
        resilience=0.9,
        capacity=0.8,
        improvement=0.7,
        compliance=1.0,
        stability=0.9,
        trust=0.8,
        adaptation=0.7,
        predictability=0.8,
        cohesion=0.9,
    )

    report = (
        FederationCognitionFusionEngine()
        .evaluate(snapshot)
    )

    assert report.strongest_dimension in (
        "performance",
        "compliance",
    )

    assert report.weakest_dimension == "risk"