from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionTrendReport:
    direction: str
    change_rate: float
    sample_count: int