from dataclasses import dataclass


@dataclass(frozen=True)
class CohesionSignal:
    federation_id: str
    cohesion_score: float
    source: str