from dataclasses import dataclass


@dataclass(frozen=True)
class PredictabilitySignal:
    federation_id: str
    predictability_score: float
    source: str