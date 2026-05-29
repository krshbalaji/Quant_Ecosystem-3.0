from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    stages: List[str] = field(default_factory=list)