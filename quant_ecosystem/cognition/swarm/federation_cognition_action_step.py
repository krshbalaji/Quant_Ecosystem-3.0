from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionActionStep:
    sequence: int
    description: str