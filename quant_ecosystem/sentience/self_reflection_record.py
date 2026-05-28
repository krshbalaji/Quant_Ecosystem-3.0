from dataclasses import dataclass


@dataclass
class SelfReflectionRecord:

    mission: str

    constitutional: bool

    survivability: float

    consistency_score: float