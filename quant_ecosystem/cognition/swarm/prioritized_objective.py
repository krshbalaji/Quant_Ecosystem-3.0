from dataclasses import dataclass


@dataclass(frozen=True)
class PrioritizedObjective:
    objective_id: str
    priority_rank: int
    score: float