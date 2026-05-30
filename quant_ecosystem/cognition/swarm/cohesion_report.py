from dataclasses import dataclass


@dataclass(frozen=True)
class CohesionReport:
    federation_id: str
    cohesion_score: float
    strongest_source: str
    signal_count: int