from dataclasses import dataclass


@dataclass(frozen=True)
class EfficiencySnapshot:
    efficiency_score: float