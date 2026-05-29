from dataclasses import dataclass


@dataclass(frozen=True)
class StrategicVote:
    organism_id: str
    decision: str
    weight: float = 1.0