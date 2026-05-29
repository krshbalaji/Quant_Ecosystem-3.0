from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPolicy:
    execution_type: str
    maximum_authorization: float
    active: bool = True