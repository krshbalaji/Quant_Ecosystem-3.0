from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionAlertReport:
    level: str
    alert_count: int