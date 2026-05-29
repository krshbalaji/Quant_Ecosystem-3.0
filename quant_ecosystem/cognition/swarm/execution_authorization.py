from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionAuthorization:
    organism_id: str
    execution_type: str
    authorized: bool
    approved_amount: float