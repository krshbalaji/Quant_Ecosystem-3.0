from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    category_name: str
    successful: bool
    stages_completed: int