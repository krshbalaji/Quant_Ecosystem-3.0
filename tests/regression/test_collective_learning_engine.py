from quant_ecosystem.cognition.swarm import (
    CollectiveLearningEngine,
    FederationObservation,
)


def test_pattern_discovery():

    engine = CollectiveLearningEngine()

    patterns = engine.discover_patterns(
        [
            FederationObservation(
                "a",
                "risk",
                "1",
                {},
            ),
            FederationObservation(
                "b",
                "risk",
                "2",
                {},
            ),
            FederationObservation(
                "c",
                "liquidity",
                "3",
                {},
            ),
        ]
    )

    categories = {
        p.category: p.frequency
        for p in patterns
    }

    assert categories["risk"] == 2