from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStageResult:
    stage_name: str
    successful: bool