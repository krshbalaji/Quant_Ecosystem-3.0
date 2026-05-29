from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionFeedbackReport:
    total_executions: int
    successful_executions: int
    success_rate: float