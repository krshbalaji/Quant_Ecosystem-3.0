from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionTrendPoint:
    timestamp: str
    cognition_index: float