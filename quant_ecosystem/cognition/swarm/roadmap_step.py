from dataclasses import dataclass


@dataclass(frozen=True)
class RoadmapStep:
    objective_id: str
    execution_order: int