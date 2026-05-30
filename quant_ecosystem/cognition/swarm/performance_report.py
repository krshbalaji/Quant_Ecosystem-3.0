from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceReport:
    total_executions: int
    successful_executions: int
    success_rate: float