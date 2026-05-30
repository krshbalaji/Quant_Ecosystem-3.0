from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionAlert:
    level: str
    message: str