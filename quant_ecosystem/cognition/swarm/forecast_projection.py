from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastProjection:
    current_count: int
    projected_count: int