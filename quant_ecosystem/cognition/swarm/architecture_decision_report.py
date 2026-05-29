from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureDecisionReport:
    recommended_category: str
    priority_score: float