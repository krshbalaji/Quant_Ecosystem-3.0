from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionResponse:
    action: str
    rationale: str