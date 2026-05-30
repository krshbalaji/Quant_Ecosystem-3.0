from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptationSignal:
    federation_id: str
    adaptation_score: float
    source: str