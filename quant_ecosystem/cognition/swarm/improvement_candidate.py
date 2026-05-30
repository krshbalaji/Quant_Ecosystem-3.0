from dataclasses import dataclass


@dataclass(frozen=True)
class ImprovementCandidate:
    category_name: str
    improvement_score: float