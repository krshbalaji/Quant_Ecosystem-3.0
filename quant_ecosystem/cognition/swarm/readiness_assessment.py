from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessAssessment:
    total_capabilities: int
    ready_capabilities: int