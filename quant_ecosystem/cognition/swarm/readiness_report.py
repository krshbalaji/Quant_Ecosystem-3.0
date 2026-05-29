from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessReport:
    operationally_ready: bool
    readiness_score: float