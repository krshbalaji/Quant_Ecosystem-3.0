from dataclasses import dataclass


@dataclass(frozen=True)
class TrustReport:
    federation_id: str
    trust_score: float
    strongest_source: str
    metric_count: int