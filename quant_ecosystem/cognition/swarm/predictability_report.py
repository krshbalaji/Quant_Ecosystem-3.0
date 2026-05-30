from dataclasses import dataclass


@dataclass(frozen=True)
class PredictabilityReport:
    federation_id: str
    predictability_score: float
    strongest_source: str
    signal_count: int