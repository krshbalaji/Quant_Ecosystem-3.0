from dataclasses import dataclass


@dataclass(frozen=True)
class StabilityIndicator:
    federation_id: str
    stability_score: float
    source: str