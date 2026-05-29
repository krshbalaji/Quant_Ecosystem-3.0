from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStep:
    step_name: str
    enabled: bool = True