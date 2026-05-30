from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptationReport:
    federation_id: str
    adaptation_score: float
    strongest_source: str
    signal_count: int