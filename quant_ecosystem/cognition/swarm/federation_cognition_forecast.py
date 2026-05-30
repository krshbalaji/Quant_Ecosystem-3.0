from dataclasses import dataclass


@dataclass(frozen=True)
class FederationCognitionForecast:
    projected_index: float
    horizon: int