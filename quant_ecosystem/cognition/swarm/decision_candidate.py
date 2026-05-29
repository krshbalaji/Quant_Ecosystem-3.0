from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionCandidate:
    category_name: str
    priority_score: float