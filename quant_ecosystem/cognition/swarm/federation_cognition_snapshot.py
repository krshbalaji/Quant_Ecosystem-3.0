from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionSnapshot:
    performance: float
    risk: float
    resilience: float
    capacity: float
    improvement: float
    compliance: float
    stability: float
    trust: float
    adaptation: float
    predictability: float
    cohesion: float