from quant_ecosystem.cognition.swarm import (
    TrustMetric,
)


def test_trust_metric():

    metric = TrustMetric(
        federation_id="FED",
        trust_score=0.95,
        source="governance",
    )

    assert metric.trust_score == 0.95