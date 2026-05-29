from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureForecastReport:
    projected_growth: int
    projected_total: int