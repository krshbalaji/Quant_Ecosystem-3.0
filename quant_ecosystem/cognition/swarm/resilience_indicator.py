from dataclasses import dataclass


@dataclass(frozen=True)
class ResilienceIndicator:
    category_name: str
    resilience_score: float