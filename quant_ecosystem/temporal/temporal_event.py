from dataclasses import dataclass


@dataclass
class TemporalEvent:

    timestamp: str

    regime: str

    survivability: float

    stress_level: float

    policy_generation: int