from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionFeedback:
    execution_id: str
    successful: bool
    stages_completed: int