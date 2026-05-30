from dataclasses import dataclass


@dataclass(frozen=True)
class ResilienceReport:
    strongest_category: str
    resilience_score: float