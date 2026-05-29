from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionInitiative:
    initiative_id: str
    description: str
    approved: bool = False