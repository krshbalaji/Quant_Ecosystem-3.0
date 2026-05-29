from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class WorkflowContext:
    values: Dict[str, Any] = field(
        default_factory=dict
    )