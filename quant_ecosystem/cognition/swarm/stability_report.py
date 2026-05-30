from dataclasses import dataclass


@dataclass(frozen=True)
class StabilityReport:
    federation_id: str
    stability_score: float
    strongest_source: str
    indicator_count: int