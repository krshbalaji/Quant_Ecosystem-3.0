from dataclasses import dataclass


@dataclass(frozen=True)
class TrustMetric:
    federation_id: str
    trust_score: float
    source: str