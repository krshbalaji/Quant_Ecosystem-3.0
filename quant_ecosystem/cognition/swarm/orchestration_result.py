from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestrationResult:
    request_id: str
    successful: bool
    stages_completed: int