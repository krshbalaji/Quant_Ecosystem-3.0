from dataclasses import dataclass
from typing import List

from .workflow_stage_result import (
    WorkflowStageResult,
)


@dataclass(frozen=True)
class WorkflowExecutionRecord:
    workflow_id: str
    successful: bool
    stage_results: List[WorkflowStageResult]