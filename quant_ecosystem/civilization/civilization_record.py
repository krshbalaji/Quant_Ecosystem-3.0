from dataclasses import dataclass


@dataclass
class CivilizationRecord:

    era_name: str

    governance_generation: int

    survivability_score: float

    doctrine_state: str

    dominant_regime: str