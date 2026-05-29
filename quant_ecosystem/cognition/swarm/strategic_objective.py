from dataclasses import dataclass


@dataclass(frozen=True)
class StrategicObjective:
    objective_id: str
    description: str
    priority: int