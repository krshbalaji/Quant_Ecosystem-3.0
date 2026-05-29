from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowExecutionSummary:
    total_steps: int
    completed_steps: int
    successful: bool