from dataclasses import dataclass


@dataclass
class StrategicObjective:

    objective_name: str

    priority: int

    survival_weight: float

    opportunity_weight: float