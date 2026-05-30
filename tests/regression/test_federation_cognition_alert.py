from quant_ecosystem.cognition.swarm import (
    FederationCognitionAlert,
)


def test_alert():

    alert = FederationCognitionAlert(
        level="INFO",
        message="ok",
    )

    assert alert.level == "INFO"