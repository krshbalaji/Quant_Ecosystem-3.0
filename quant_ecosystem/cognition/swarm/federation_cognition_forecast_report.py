from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionForecastReport:
    current_index: float
    projected_index: float
    direction: str
    horizon: int