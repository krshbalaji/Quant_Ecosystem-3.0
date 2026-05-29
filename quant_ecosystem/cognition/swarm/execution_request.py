from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionRequest:
    organism_id: str
    execution_type: str
    requested_amount: float