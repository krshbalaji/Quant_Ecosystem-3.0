from dataclasses import dataclass


@dataclass(frozen=True)
class PrioritizationScore:
    objective_id: str
    score: float